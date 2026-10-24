from common import probe_version
DOMAIN_ID="CLI_CPP23_TOOLCHAIN"
def probe():
    compilers=[probe_version(x,["--version"]) for x in ("g++","clang++")]
    cmake=probe_version("cmake",["--version"]); ninja=probe_version("ninja",["--version"])
    source="#include <version>\nint main() { return 0; }\n"
    tests=[probe_version(x,["-std=c++23","-x","c++","-fsyntax-only","-"],30,source) for x in ("g++","clang++")]
    accepted=[x["binary"] for x in tests if x["status"]=="PASS"]
    status="AVAILABLE" if accepted and cmake["status"]=="PASS" and ninja["status"]=="PASS" else ("PARTIAL" if any(x["status"]!="ABSENT" for x in compilers+[cmake,ninja]) else "ABSENT")
    return {"domain_id":DOMAIN_ID,"status":status,"probes":compilers+[cmake,ninja],
            "cxx23_smoke":{"status":"PASS" if accepted else "FAIL","accepted_compilers":accepted,"results":tests},
            "read_only":True,"mutations_performed":False,"certification":"NOT_GRANTED"}
