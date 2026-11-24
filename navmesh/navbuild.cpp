// navbuild: triangle soup (Unreal coordinates, cm) -> Recast solo navmesh -> NavKit navp.json (Deathtrap/Knt layout)
// One NavGraph per agent: "NavPower Base" (r42 h192) and "NavPower Large" (r80 h360), both step 35.
// Usage: navbuild <in.tris> <out.navp.json>
//   in.tris: text, one triangle per line: x0 y0 z0 x1 y1 z1 x2 y2 z2 (Unreal X Y Z)
#include "Recast.h"
#include <cmath>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

struct Agent { const char* name; float radius, height, step; };

// Unreal (X,Y,Z up) -> Recast (x, y up, z): x=X, y=Z, z=-Y  (proper rotation)
static void toRecast(const float* ue, float* rc) { rc[0] = ue[0]; rc[1] = ue[2]; rc[2] = -ue[1]; }

static bool buildGraph(const std::vector<float>& verts, const std::vector<int>& tris, const Agent& ag,
                       std::ostringstream& out, int& areaCount) {
    rcContext ctx(false);
    const float cs = 10.0f, ch = 10.0f;
    float bmin[3], bmax[3];
    rcCalcBounds(verts.data(), (int)verts.size() / 3, bmin, bmax);
    bmin[1] -= 50; bmax[1] += ag.height;

    rcConfig cfg{};
    cfg.cs = cs; cfg.ch = ch;
    cfg.walkableSlopeAngle = 45.0f;
    cfg.walkableHeight = (int)std::ceil(ag.height / ch);
    cfg.walkableClimb = (int)std::floor(ag.step / ch);
    cfg.walkableRadius = (int)std::ceil(ag.radius / cs);
    cfg.maxEdgeLen = (int)(1200.0f / cs);
    cfg.maxSimplificationError = 1.3f;
    cfg.minRegionArea = 8 * 8;
    cfg.mergeRegionArea = 20 * 20;
    cfg.maxVertsPerPoly = 6;
    cfg.detailSampleDist = cs * 6; cfg.detailSampleMaxError = ch;
    rcVcopy(cfg.bmin, bmin); rcVcopy(cfg.bmax, bmax);
    rcCalcGridSize(cfg.bmin, cfg.bmax, cfg.cs, &cfg.width, &cfg.height);

    rcHeightfield* hf = rcAllocHeightfield();
    if (!rcCreateHeightfield(&ctx, *hf, cfg.width, cfg.height, cfg.bmin, cfg.bmax, cfg.cs, cfg.ch)) return false;
    const int ntris = (int)tris.size() / 3;
    std::vector<unsigned char> areas(ntris, 0);
    rcMarkWalkableTriangles(&ctx, cfg.walkableSlopeAngle, verts.data(), (int)verts.size() / 3, tris.data(), ntris, areas.data());
    if (!rcRasterizeTriangles(&ctx, verts.data(), (int)verts.size() / 3, tris.data(), areas.data(), ntris, *hf, cfg.walkableClimb)) return false;
    rcFilterLowHangingWalkableObstacles(&ctx, cfg.walkableClimb, *hf);
    rcFilterLedgeSpans(&ctx, cfg.walkableHeight, cfg.walkableClimb, *hf);
    rcFilterWalkableLowHeightSpans(&ctx, cfg.walkableHeight, *hf);

    rcCompactHeightfield* chf = rcAllocCompactHeightfield();
    if (!rcBuildCompactHeightfield(&ctx, cfg.walkableHeight, cfg.walkableClimb, *hf, *chf)) return false;
    if (!rcErodeWalkableArea(&ctx, cfg.walkableRadius, *chf)) return false;
    if (!rcBuildDistanceField(&ctx, *chf)) return false;
    if (!rcBuildRegions(&ctx, *chf, 0, cfg.minRegionArea, cfg.mergeRegionArea)) return false;
    rcContourSet* cset = rcAllocContourSet();
    if (!rcBuildContours(&ctx, *chf, cfg.maxSimplificationError, cfg.maxEdgeLen, *cset)) return false;
    rcPolyMesh* pm = rcAllocPolyMesh();
    if (!rcBuildPolyMesh(&ctx, *cset, cfg.maxVertsPerPoly, *pm)) return false;

    const int nvp = pm->nvp;
    areaCount = 0;
    out << "{\"Areas\":[";
    bool firstArea = true;
    for (int i = 0; i < pm->npolys; ++i) {
        const unsigned short* p = &pm->polys[i * nvp * 2];
        std::vector<float> ux, uy, uz; std::vector<int> nei;
        for (int j = 0; j < nvp && p[j] != RC_MESH_NULL_IDX; ++j) {
            const unsigned short* v = &pm->verts[p[j] * 3];
            float rc[3] = {pm->bmin[0] + v[0] * pm->cs, pm->bmin[1] + v[1] * pm->ch, pm->bmin[2] + v[2] * pm->cs};
            ux.push_back(rc[0]); uy.push_back(-rc[2]); uz.push_back(rc[1]);
            unsigned short n = p[nvp + j];
            nei.push_back((n == RC_MESH_NULL_IDX || (n & 0x8000)) ? -1 : (int)n);
        }
        const int n = (int)ux.size();
        if (n < 3) continue;
        double s = 0;
        for (int k = 0; k < n; ++k) s += (double)ux[k] * uy[(k + 1) % n] - (double)ux[(k + 1) % n] * uy[k];
        std::vector<int> order(n), edgeNei(n);
        if (s > 0) { for (int k = 0; k < n; ++k) { order[k] = k; edgeNei[k] = nei[k]; } }
        else { for (int k = 0; k < n; ++k) { order[k] = n - 1 - k; edgeNei[k] = nei[((n - 2 - k) % n + n) % n]; } }
        if (!firstArea) out << ",";
        firstArea = false;
        out << "{\"Area\":{\"Index\":" << (i + 1) << ",\"Type\":\"UNKNOWN!\"},\"Edges\":[";
        for (int k = 0; k < n; ++k) {
            if (k) out << ",";
            out << "{";
            if (edgeNei[k] >= 0) out << "\"Adjacent Area\":" << (edgeNei[k] + 1) << ",";
            char buf[160];
            snprintf(buf, sizeof buf, "\"Position\":{\"X\":%.4f,\"Y\":%.4f,\"Z\":%.4f}}", ux[order[k]], uy[order[k]], uz[order[k]]);
            out << buf;
        }
        out << "]}";
        ++areaCount;
    }
    out << "]}";
    rcFreePolyMesh(pm); rcFreeContourSet(cset); rcFreeCompactHeightfield(chf); rcFreeHeightField(hf);
    return true;
}

int main(int argc, char** argv) {
    if (argc < 3) { fprintf(stderr, "usage: navbuild <in.tris> <out.navp.json>\n"); return 1; }
    std::ifstream in(argv[1]);
    std::vector<float> verts; std::vector<int> tris;
    float t[9];
    while (in >> t[0] >> t[1] >> t[2] >> t[3] >> t[4] >> t[5] >> t[6] >> t[7] >> t[8]) {
        for (int k = 0; k < 3; ++k) { float rc[3]; toRecast(&t[k * 3], rc); verts.insert(verts.end(), rc, rc + 3); tris.push_back((int)tris.size()); }
    }
    fprintf(stderr, "%d triangles\n", (int)tris.size() / 3);
    const Agent agents[2] = {{"NavPower Base", 42, 192, 35}, {"NavPower Large", 80, 360, 35}};
    std::ostringstream out;
    out << "{\"NavpJsonVersion\":\"0.3\",\"Game\":\"Knt\",\"Sections\":[{\"NavGraphs\":[";
    for (int a = 0; a < 2; ++a) {
        int count = 0;
        if (a) out << ",";
        if (!buildGraph(verts, tris, agents[a], out, count)) { fprintf(stderr, "build failed for %s\n", agents[a].name); return 2; }
        fprintf(stderr, "%s: %d areas\n", agents[a].name, count);
        if (count == 0) { fprintf(stderr, "no walkable area for %s\n", agents[a].name); return 3; }
    }
    out << "]}]}";
    std::ofstream(argv[2]) << out.str();
    return 0;
}
