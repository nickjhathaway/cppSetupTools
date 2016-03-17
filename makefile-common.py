#!/usr/bin/env python

import subprocess, sys, os, argparse
from collections import namedtuple
import shutil
sys.path.append(os.path.join(os.path.dirname(__file__), "scripts/pyUtils"))
sys.path.append(os.path.join(os.path.dirname(__file__), "scripts/setUpScripts"))
from utils import Utils
from genFuncs import genHelper 
from color_text import ColorText as CT

class AllLibCompFlags():
    
    def __init__(self, externalLoc):
        self.base_dir = os.path.abspath(externalLoc); #top dir to hold tars,build, local directories
        self.install_dir = os.path.join(self.base_dir, "local") #location for the final install of programs/libraries
        self.libs_ = {}
        self.libs_["zi_lib"] = self.__zi_lib()
        self.libs_["pstreams"] = self.__pstreams()
        self.libs_["cppitertools"] = self.__cppitertools()
        self.libs_["cppprogutils"] = self.__cppprogutils()
        self.libs_["r"] = self.__r()
        self.libs_["jsoncpp"] = self.__jsoncpp()
        self.libs_["twobit"] = self.__twobit()
        self.libs_["cppcms"] = self.__cppcms()
        self.libs_["armadillo"] = self.__armadillo()
        self.libs_["bamtools"] = self.__bamtools()
        self.libs_["catch"] = self.__catch()
        self.libs_["dlib"] = self.__dlib()
        self.libs_["libsvm"] = self.__libsvm()
        self.libs_["boost"] = self.__boost()
        self.libs_["mongoc"] = self.__mongoc()
        self.libs_["mongocxx"] = self.__mongocxx()
        self.libs_["bibcpp"] = self.__bibcpp()
        self.libs_["bibseq"] = self.__bibseq()
        self.libs_["bibseqdev"] = self.__bibseqDev()
        self.libs_["njhrinside"] = self.__njhRInside()
        self.libs_["seqserver"] = self.__seqServer()
        self.libs_["seekdeepdev"] = self.__SeekDeepDev()
        self.libs_["seekdeep"] = self.__SeekDeep()
        self.libs_["sharedmutex"] = self.__sharedMutex()
        """
        self.libs_["mathgl"] = self.__mathgl()
        self.libs_["mlpack"] = self.__mlpack()
        self.libs_["liblinear"] = self.__liblinear()
        """

    
    def __twobit(self):
        libName = "TwoBit"
        lib = LibCompFlags(libName, "1.0")
        lib.addVersion("1.0",[LibNameVer("cppitertools", "v0.1"),LibNameVer("cppprogutils", "1.0")])
        lib.addVersion("develop",[LibNameVer("cppitertools", "v0.1"),LibNameVer("cppprogutils", "develop")])
        return lib

    def __bibcpp(self):
        libName = "bibcpp"
        lib = LibCompFlags(libName, "develop")
        lib.addHeaderOnly("develop",[LibNameVer("jsoncpp", "1.6.5"),LibNameVer("boost", "1_60_0"),LibNameVer("cppitertools", "v0.1"),LibNameVer("pstreams", "RELEASE_0_8_1")])
        lib.versions_["develop"].additionalLdFlags_ = ["-lpthread", "-lz", "-lrt"] 
        lib.addHeaderOnly("2.2.1",[LibNameVer("jsoncpp", "1.6.5"),LibNameVer("boost", "1_58_0"),LibNameVer("cppitertools", "v0.1"),LibNameVer("pstreams", "RELEASE_0_8_1")])
        lib.versions_["2.2.1"].additionalLdFlags_ = ["-lpthread", "-lz", "-lrt"] 
        return lib
     
    def __bibseq(self):
        libName = "bibseq"
        lib = LibCompFlags(libName, "develop")
        lib.addVersion("develop",[LibNameVer("bibcpp", "develop"),LibNameVer("twobit", "develop"),LibNameVer("bamtools", "2.4.0"),LibNameVer("armadillo", "6.200.3")])
        lib.versions_["develop"].additionalLdFlags_ = ["-lcurl"] 
        lib.addVersion("2.2.1",[LibNameVer("bibcpp", "2.2.1"),LibNameVer("bamtools", "2.4.0"),LibNameVer("armadillo", "6.200.3")])
        lib.versions_["2.2.1"].additionalLdFlags_ = ["-lcurl"] 
        return lib
    
    def __bibseqDev(self):
        libName = "bibseqDev"
        lib = LibCompFlags(libName, "master")
        lib.addVersion("master",[LibNameVer("bibcpp", "develop"),LibNameVer("twobit", "develop"),LibNameVer("curl", "default"),LibNameVer("bamtools", "2.4.0"),LibNameVer("armadillo", "6.200.3")])
        return lib

    def __njhRInside(self):
        libName = "njhRInside"
        lib = LibCompFlags(libName, "develop")
        lib.addVersion("develop",[LibNameVer("R", "3.2.2"),LibNameVer("cppitertools", "v0.1")])
        lib.addVersion("1.1.1",[LibNameVer("R", "3.2.2"),LibNameVer("cppitertools", "v0.1")])
        return lib

    def __seqServer(self):
        libName = "seqServer"
        lib = LibCompFlags(libName, "develop")
        lib.addVersion("develop",[LibNameVer("bibseq", "develop"),LibNameVer("cppcms", "1.0.5")])
        lib.addVersion("1.2.1",[LibNameVer("bibseq", "2.2.1"),LibNameVer("cppcms", "1.0.5")])
        return lib

    def __SeekDeepDev(self):
        libName = "SeekDeepDev"
        lib = LibCompFlags(libName, "master")
        lib.addVersion("master",[LibNameVer("bibseqDev", "master"),LibNameVer("seqServer", "develop")])
        return lib
        
    def __SeekDeep(self):
        libName = "SeekDeep"
        lib = LibCompFlags(libName, "develop")
        lib.addVersion("develop",[LibNameVer("bibseq", "develop"),LibNameVer("njhRInside", "develop"),LibNameVer("seqServer", "develop")])
        lib.addVersion("2.2.1",[LibNameVer("bibseq", "2.2.1"),LibNameVer("njhRInside", "1.1.1"),LibNameVer("seqServer", "1.2.1")])
        return lib
    
    def __sharedMutex(self):
        libName = "sharedMutex"
        lib = LibCompFlags(libName, "v0.1")
        lib.addVersion("v0.1")
        lib.addVersion("develop")
        return lib
    
    def getLibNames(self):
        return sorted(self.libs_.keys())
    
    def checkForLibVer(self, verName):
        if verName.name not in self.libs_:
            raise Exception("Lib " + verName.name + " not found in libs, options are " + ", ".join(self.getLibNames()))
        else:
            if verName.version not in self.libs_[verName.name].versions_:
                raise Exception("Version " + verName.version + " for lib " \
                                + verName.name + " not found in available versions, options are " \
                                + ", ".join(self.libs_[verName.name].getVersions()))
                
    def getLdFlags(self, verName):
        self.checkForLibVer(verName)
        return self.libs_[verName.name].versions_[verName.version].getLdFlags(self.install_dir)
    
    def getIncludeFlags(self, verName):
        self.checkForLibVer(verName)
        return self.libs_[verName.name].versions_[verName.version].getIncludeFlags(self.install_dir)
    
    def isInstalled(self, verName):
        if os.path.exists(os.path.join(self.install_dir, joinNameVer(verName))):
            return True
        else:
            return False
    
    def getDefaultIncludeFlags(self):
        return "-I./src/"
    
    def getDefaultLDFlags(self):
        ret = ""
        if Utils.isMac():
            #for dylib path fixing in macs, this gets rid of the name_size limit, which why the hell is there a name size limit
            ret = ret + "-headerpad_max_install_names" 
        return ret
        


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--externalDir', type=str, required = True)
    parser.add_argument('--list',  action = "store_true")
    return parser.parse_args()

def main():
    args = parse_args()
    flagGenerator = AllLibCompFlags(args.externalDir)
    if args.list:
        libs = flagGenerator.getLibNames()
        for lib in libs:
            print(lib)
            vers = flagGenerator.libs_[lib].getVersions()
            sys.stdout.write("\t")
            sys.stdout.write(",".join(vers))
            sys.stdout.write("\n")
    

if __name__ == '__main__':
    main()
