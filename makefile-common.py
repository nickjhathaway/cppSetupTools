#!/usr/bin/env python



import subprocess, sys, os, argparse
from collections import namedtuple
import shutil
sys.path.append("scripts/pyUtils")
sys.path.append("scripts/setUpScripts")
from utils import Utils
from genFuncs import genHelper 
from color_text import ColorText as CT


def runAndCapture(cmd):
    # print CT.boldRed("before process")
    # from http://stackoverflow.com/a/4418193
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    #print CT.boldRed("after process")
    # Poll process for new output until finished
    actualOutput = ""
    while True:
        nextline = process.stdout.readline()
        if nextline == '' and process.poll() != None:
            break
        actualOutput = actualOutput + nextline
        #sys.stdout.write(nextline)
        #sys.stdout.flush()

    output = process.communicate()[0]
    exitCode = process.returncode
    #print "exit code "  + CT.boldRed(str(exitCode))
    if (exitCode == 0):
        return actualOutput
        #return output
    raise Exception(cmd, exitCode, output)


LibNameVer = namedtuple("LibNameVer", 'name version')


def joinNameVer(libNameVerTup):
    return os.path.join(libNameVerTup.name, libNameVerTup.version, libNameVerTup.name)

class LibVersionCompFlagsR():
    def __init__(self, name, version):
        self.nameVer_ = LibNameVer(name, version)
        self.rInstallLoc_ = ""
        self.rExecutable_ = ""
        self.rHome_ = ""

        
    def setExecutableLoc(self, localPath):
        self.rInstallLoc_ = os.path.join(os.path.abspath(localPath), joinNameVer(self.nameVer_))
        if Utils.isMac():
            self.rExecutable_ = os.path.join(self.rInstallLoc_, "R.framework/Resources/bin/R")
        else:
            self.rExecutable_ = os.path.join(self.rInstallLoc_, "bin/R")
        self.rHome_ = runAndCapture(self.rExecutable_ + " RHOME")
    
    def getIncludeFlags(self, localPath):
        self.setExecutableLoc(localPath)
        ret = "-DSTRICT_R_HEADERS"
        ret = ret + " " + runAndCapture(self.rExecutable_ + " CMD config --cppflags")
        ret = ret + " " + runAndCapture("echo 'Rcpp:::CxxFlags()' | " + self.rExecutable_ + " --vanilla --slave")
        ret = ret + " " + runAndCapture("echo 'RInside:::CxxFlags()' | " + self.rExecutable_ + " --vanilla --slave")
        return ' '.join(ret.split())
        
    def getLdFlags(self, localPath):
        self.setExecutableLoc(localPath)
        ret = ""
        ret = ret + runAndCapture(self.rExecutable_ + " CMD config --ldflags")
        ret = ret + " " + runAndCapture(self.rExecutable_ + " CMD config BLAS_LIBS")
        ret = ret + " " + runAndCapture(self.rExecutable_ + " CMD config LAPACK_LIBS")
        ret = ret + " " + "-Wl,-rpath," + self.rHome_ + "/lib"
        ret = ret + " " + runAndCapture("echo 'Rcpp:::LdFlags()' | " + self.rExecutable_ + " --vanilla --slave")
        ret = ret + " " + runAndCapture("echo 'RInside:::LdFlags()' | " + self.rExecutable_ + " --vanilla --slave")
        return ' '.join(ret.split())


class LibVersionCompFlags():
    def __init__(self, name, version, depends):
        self.nameVer_ = LibNameVer(name, version)
        self.depends_ = depends #should be a list of LibNameVer
        self.includePath_ = os.path.join(joinNameVer(self.nameVer_), "include")
        self.libPath_ = os.path.join(joinNameVer(self.nameVer_), "lib")
        self.additionalLdFlags_ = []
        
    def getIncludeFlags(self, localPath):
        ret = ""
        if(len(self.includePath_) > 0):
            ret = "-isystem" + str(os.path.join(localPath, self.includePath_))
        return ret
    
    def getLdFlags(self, localPath):
        ret = ""
        retList = []
        libPath = str(os.path.join(localPath,self.libPath_))
        if(len(self.libPath_) > 0):
            retList.append("-Wl,-rpath," + str(libPath))
            retList.append("-L" + str(libPath))
            retList.append("-l" + self.nameVer_.name)
        if(len(self.additionalLdFlags_) > 0):
            retList.extend(self.additionalLdFlags_)
        if(len(retList) > 0):
            ret = " ".join(retList)                 
        return ret
    
    

class LibCompFlags():
    def __init__(self, name, defaultVersion):
        self.name_ = name
        self.defaultVersion_ = defaultVersion
        self.versions_ = {}
    
    def getVersions(self):
        return sorted(self.versions_.keys())
    
    def addHeaderOnly(self, version,  depends=[]):
        self.versions_[version] = LibVersionCompFlags(self.name_, version, depends)
        self.versions_[version].includePath_ = joinNameVer(self.versions_[version].nameVer_)
        self.versions_[version].libPath_ = ""
    
    def addVersion(self, version, depends=[]):
        self.versions_[version] = LibVersionCompFlags(self.name_, version,depends)

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
        self.libs_["curl"] = self.__curl()
        self.libs_["dlib"] = self.__dlib()
        self.libs_["libsvm"] = self.__libsvm()
        self.libs_["boost"] = self.__boost()
        """
        self.libs_["mathgl"] = self.__mathgl()
        
        self.libs_["mlpack"] = self.__mlpack()
        self.libs_["liblinear"] = self.__liblinear()
        self.libs_["bibseq"] = self.__bibseq()
        self.libs_["bibcpp"] = self.__bibcpp()
        self.libs_["seekdeep"] = self.__SeekDeep()
        self.libs_["bibseqdev"] = self.__bibseqDev()
        self.libs_["seekdeepdev"] = self.__SeekDeepDev()
        self.libs_["seqserver"] = self.__seqserver()
        self.libs_["njhrinside"] = self.__njhRInside()
        
        
        self.libs_["mongoc"] = self.__mongoc()
        self.libs_["mongocxx"] = self.__mongocxx()
        
        """
    def __zi_lib(self):
        libName = "zi_lib"
        lib = LibCompFlags(libName, "master")
        lib.addHeaderOnly("master")
        lib.versions_["master"].additionalLdFlags_ = ["-lrt"]
        return lib
    
    def __cppitertools(self):
        libName = "cppitertools"
        lib = LibCompFlags(libName, "v0.1")
        lib.addHeaderOnly("master")
        lib.addHeaderOnly("v0.1")
        return lib
    
    def __pstreams(self):
        libName = "pstreams"
        lib = LibCompFlags(libName, "RELEASE_0_8_1")
        lib.addHeaderOnly("RELEASE_0_8_1")
        lib.addHeaderOnly("master")
        return lib
    
    def __cppprogutils(self):
        libName = "cppprogutils"
        lib = LibCompFlags(libName, "master")
        lib.addHeaderOnly("master",[LibNameVer("cppitertools", "v0.1")])
        lib.versions_["master"].additionalLdFlags_ = ["-lpthread"]
        lib.addHeaderOnly("develop",[LibNameVer("cppitertools", "v0.1")])
        lib.versions_["develop"].additionalLdFlags_ = ["-lpthread"]
        lib.addHeaderOnly("1.0",[LibNameVer("cppitertools", "v0.1")])
        lib.versions_["1.0"].additionalLdFlags_ = ["-lpthread"]
        return lib
    
    def __r(self):
        libName = "R"
        lib = LibCompFlags(libName, "3.2.2")
        lib.versions_["3.2.2"] = LibVersionCompFlagsR("R", "3.2.2")
        lib.versions_["3.2.1"] = LibVersionCompFlagsR("R", "3.2.1")
        lib.versions_["3.2.0"] = LibVersionCompFlagsR("R", "3.2.0")
        lib.versions_["3.1.3"] = LibVersionCompFlagsR("R", "3.1.3")
        return lib

    def __jsoncpp(self):
        libName = "jsoncpp"
        lib = LibCompFlags(libName, "1.6.5")
        lib.addVersion("1.6.5")
        lib.addVersion("master")
        return lib
    
    def __twobit(self):
        libName = "TwoBit"
        lib = LibCompFlags(libName, "1.0")
        lib.addVersion("1.0",[LibNameVer("cppitertools", "v0.1"),LibNameVer("cppprogutils", "1.0")])
        lib.addVersion("master",[LibNameVer("cppitertools", "v0.1"),LibNameVer("cppprogutils", "1.0")])
        lib.addVersion("develop",[LibNameVer("cppitertools", "v0.1"),LibNameVer("cppprogutils", "develop")])
        return lib
    
    def __cppcms(self):
        libName = "cppcms"
        lib = LibCompFlags(libName, "1.0.5")
        lib.addVersion("1.0.5")
        lib.versions_["1.0.5"].additionalLdFlags_ = ["-lbooster"]
        return lib

    def __armadillo(self):
        libName = "armadillo"
        lib = LibCompFlags(libName, "6.200.3")
        lib.addVersion("6.200.3")
        lib.addVersion("6.100.0")
        lib.addVersion("5.600.2")
    
    def __bamtools(self):
        libName = "bamtools"
        lib = LibCompFlags(libName, "2.4.0")
        lib.addVersion("2.4.0")
        lib.versions_["2.4.0"].libPath_ = os.join(lib.versions_["2.4.0"].libPath_,libName)
        lib.versions_["2.4.0"].includePath_ = os.join(lib.versions_["2.4.0"].includePath_,libName)
        lib.addVersion("2.3.0")
        lib.versions_["2.3.0"].libPath_ = os.join(lib.versions_["2.3.0"].libPath_,libName)
        lib.versions_["2.3.0"].includePath_ = os.join(lib.versions_["2.3.0"].includePath_,libName)
        return lib
    
    def __catch(self):
        libName = "catch"
        lib = LibCompFlags(libName, "v1.3.3")
        lib.addVersion("v1.3.3")
        lib.versions_["v1.3.3"].includePath_ = os.path.join(joinNameVer(lib.versions_["2.4.0"].nameVer_), "single_include")
        return lib

    def __curl(self):
        libName = "curl"
        lib = LibCompFlags(libName, "default")
        lib.addHeaderOnly("default")
        lib.versions_["default"].includePath_ = ""
        return lib
        
    def __dlib(self):
        libName = "dlib"
        lib = LibCompFlags(libName, "18.7")
        lib.addHeaderOnly("18.7")
        
    def __libsvm(self):
        libName = "libsvm"
        lib = LibCompFlags(libName, "3.18")
        lib.addHeaderOnly("3.18")
        return lib
    
    def __boost(self):
        libName = "boost"
        lib = LibCompFlags(libName, "1_60_0")
        lib.addVersion("1_60_0")
        lib.versions_["1_60_0"].additionalLdFlags_ = ["-lboost_system", "-lboost_filesystem","-lboost_iostreams"]
        lib.addVersion("1_59_0")
        lib.versions_["1_59_0"].additionalLdFlags_ = ["-lboost_system", "-lboost_filesystem","-lboost_iostreams"]
        lib.addVersion("1_58_0")
        lib.versions_["1_58_0"].additionalLdFlags_ = ["-lboost_system", "-lboost_filesystem","-lboost_iostreams"]
        return lib
    
    #1.2.0-dev
    #master
    #LibNameVer = namedtuple("LibNameVer", 'name version')
    
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
    return parser.parse_args()

def main():
    args = parse_args()
    flagGenerator = AllLibCompFlags(args.externalDir)
    print(flagGenerator.getIncludeFlags(LibNameVer("cppprogutils", "master")))
    print(flagGenerator.getLdFlags(LibNameVer("cppprogutils", "master")))
    

if __name__ == '__main__':
    main()
