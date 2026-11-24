#include "include/NavWeakness/NavWeakness.h"
#include <cstdio>
#include <cstring>
int main(int argc, char** argv) {
    if (argc < 4) { printf("usage: navtool <binary|json> <in> <out.navp> [out.json]\n"); return 1; }
    bool fromJson = strcmp(argv[1], "json") == 0;
    NavPower::NavMesh m = fromJson ? NavWeakness::LoadNavMeshFromJson(argv[2]) : NavWeakness::LoadNavMeshFromBinary(argv[2]);
    NavWeakness::OutputNavMesh_NAVP_Write(&m, argv[3]);
    if (argc > 4) NavWeakness::OutputNavMesh_JSON_Write(&m, argv[4]);
    printf("ok\n");
    return 0;
}
