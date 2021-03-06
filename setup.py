#!/usr/bin/env python



import subprocess, sys, os, argparse,shutil
from collections import namedtuple
sys.path.append(os.path.join(os.path.dirname(__file__), "scripts/pyUtils"))
sys.path.append(os.path.join(os.path.dirname(__file__), "scripts/setUpScripts"))
from utils import Utils
from genFuncs import genHelper 
from color_text import ColorText as CT
import pickle, datetime

#tuples
BuildPaths = namedtuple("BuildPaths", 'url build_dir build_sub_dir local_dir')
LibNameVer = namedtuple("LibNameVer", 'name version')
GitRefs = namedtuple("GitRefs", "branches tags")


class LibDirMaster():
    def __init__(self,externalLoc):
        self.base_dir = os.path.abspath(externalLoc); #top dir to hold tars,build, local directories
        
        self.ext_tars = os.path.join(self.base_dir, "tarballs") #location to keep tarballs of programs/libraries downloads
        self.ext_build = os.path.join(self.base_dir, "build") #location for the building of programs/libraries
        self.install_dir = os.path.join(self.base_dir, "local") #location for the final install of programs/libraries
        self.cache_dir = os.path.join(self.base_dir, ".cache")
        
        Utils.mkdir(self.ext_tars) #tar storage directory
        Utils.mkdir(self.ext_build) #build directory
        Utils.mkdir(self.install_dir) #local directory
        Utils.mkdir(self.cache_dir) #cache directory

def joinNameVer(libNameVerTup):
    return os.path.join(libNameVerTup.name, libNameVerTup.version, libNameVerTup.name)

class CPPLibPackageVersionR():
    def __init__(self, name, url, version, dirMaster):
        self.nameVer_ = LibNameVer(name, version)
        build_dir = os.path.join(dirMaster.ext_build, name, version)
        fn = os.path.basename(url)
        fn_noex = fn.replace(".tar.gz", "").replace(".tar.bz2", "").replace(".git", "")
        build_sub_dir = os.path.join(dirMaster.ext_build, name, version, fn_noex)
        local_dir = os.path.join(dirMaster.install_dir, name, version, name)
        self.bPaths_ = BuildPaths(url, build_dir, build_sub_dir, local_dir)
        self.rInstallLoc_ = ""
        self.rExecutable_ = ""
        self.rHome_ = ""
        self.depends_ = []
        
        
    def setExecutableLoc(self, localPath):
        self.rInstallLoc_ = os.path.join(os.path.abspath(localPath), joinNameVer(self.nameVer_))
        if Utils.isMac():
            self.rExecutable_ = os.path.join(self.rInstallLoc_, "R.framework/Resources/bin/R")
        else:
            self.rExecutable_ = os.path.join(self.rInstallLoc_, "bin/R")
        self.rHome_ = str(Utils.runAndCapture(self.rExecutable_ + " RHOME")).strip()
    
    def getIncludeFlags(self, localPath):
        self.setExecutableLoc(localPath)
        ret = "-DSTRICT_R_HEADERS"
        ret = ret + " " + Utils.runAndCapture(self.rExecutable_ + " CMD config --cppflags")
        ret = ret + " " + Utils.runAndCapture("echo 'Rcpp:::CxxFlags()' | " + self.rExecutable_ + " --vanilla --slave")
        ret = ret + " " + Utils.runAndCapture("echo 'RInside:::CxxFlags()' | " + self.rExecutable_ + " --vanilla --slave")
        return ' '.join(ret.split())
        
    def getLdFlags(self, localPath):
        self.setExecutableLoc(localPath)
        ret = ""
        ret = ret + Utils.runAndCapture(self.rExecutable_ + " CMD config --ldflags")
        ret = ret + " " + Utils.runAndCapture(self.rExecutable_ + " CMD config BLAS_LIBS")
        ret = ret + " " + Utils.runAndCapture(self.rExecutable_ + " CMD config LAPACK_LIBS")
        ret = ret + " " + "-Wl,-rpath," + self.rHome_ + "/lib"
        ret = ret + " " + Utils.runAndCapture("echo 'Rcpp:::LdFlags()' | " + self.rExecutable_ + " --vanilla --slave")
        ret = ret + " " + Utils.runAndCapture("echo 'RInside:::LdFlags()' | " + self.rExecutable_ + " --vanilla --slave")
        return ' '.join(ret.split())
    
    def getDownloadUrl(self):
        return self.bPaths_.url


class CPPLibPackageVersion():
    def __init__(self, name, version, bPaths, depends):
        self.nameVer_ = LibNameVer(name, version)
        self.depends_ = depends #should be a list of LibNameVer
        self.bPaths_ = bPaths
        self.includePath_ = os.path.join(joinNameVer(self.nameVer_), "include")
        self.additionalIncludeFlags_ = []
        self.additionalIncludePaths_ = []
        self.libPath_ = os.path.join(joinNameVer(self.nameVer_), "lib")
        self.additionalLdFlags_ = []
        self.libName_ = name
        self.altLibName_ = ""
        
        
    def getDownloadUrl(self):
        ret = self.bPaths_.url
        if str(self.bPaths_.url).endswith(".git"):
            ret = self.bPaths_.url.replace(".git","/archive/" + str(self.nameVer_.version) + ".tar.gz").replace("git@github.com:", "https://github.com/")
        return ret
    
    def getIncludeFlags(self, localPath):
        ret = ""
        if(len(self.includePath_) > 0):
            ret = "-isystem" + str(os.path.join(localPath, self.includePath_))
        if len(self.additionalIncludePaths_) > 0:
            for addPath in self.additionalIncludePaths_:
                if len(ret) > 0:
                    ret = ret + " "
                ret = ret + "-isystem" + str(os.path.join(localPath, addPath))
        if len(self.additionalIncludeFlags_) > 0:
            if len(ret)> 0:
                ret = ret + " "
            ret = ret + " ".join(self.additionalIncludeFlags_) 
        return ret
    
    def getLdFlags(self, localPath):
        ret = ""
        retList = []
        libPath = str(os.path.join(localPath,self.libPath_))
        if(len(self.libPath_) > 0):
            retList.append("-Wl,-rpath," + str(libPath))
            retList.append("-L" + str(libPath))
            if len(self.altLibName_) > 0:
                retList.append("-l" + self.altLibName_)
            elif "" != self.libName_:
                retList.append("-l" + self.libName_)
        if len(self.additionalLdFlags_) > 0:
            retList.extend(self.additionalLdFlags_)
        if len(retList) > 0:
            ret = " ".join(retList)                 
        return ret
    

class CPPLibPackage():
    def __init__(self, name, defaultBuildCmd, dirMaster, libType, defaultVersion):
        self.name_ = name
        
        self.defaultVersion_ = defaultVersion.replace("/", "__")
        self.defaultBuildCmd_ = defaultBuildCmd
        self.versions_ = {}
        self.externalLibDir_ = dirMaster
        if "git" != libType and "file" != libType and "git-headeronly" != libType:
            raise Exception("libType should be 'git', 'git-headeronly', or 'file', not " + str(libType))
        self.libType_ = libType #should be git, git-headeronly, or file
        self.bibProject_ = False
    
    def addVersion(self, url, verName, depends=[]):
        verName = verName.replace("/", "__")
        build_dir = os.path.join(self.externalLibDir_.ext_build, self.name_, verName)
        fn = os.path.basename(url)
        fn_noex = fn.replace(".tar.gz", "").replace(".tar.bz2", "").replace(".git", "")
        build_sub_dir = os.path.join(self.externalLibDir_.ext_build, self.name_, verName, self.name_)
        local_dir = os.path.join(self.externalLibDir_.install_dir, self.name_, verName, self.name_)
        self.versions_[verName] = CPPLibPackageVersion(self.name_, verName,BuildPaths(url, build_dir, build_sub_dir, local_dir), depends)
    
    def addHeaderOnlyVersion(self, url, verName, depends=[]):
        '''set up for header only libraries, these just need
         the header copied no need for build_dir build_sub_dir '''
        verName = verName.replace("/", "__")
        local_dir = os.path.join(self.externalLibDir_.install_dir, self.name_, verName, self.name_)
        self.versions_[verName] = CPPLibPackageVersion(self.name_, verName,BuildPaths(url, "", "", local_dir), depends)
        self.versions_[verName].includePath_ = os.path.join(self.name_, verName)
        #self.versions_[verName].includePath_ = joinNameVer(self.versions_[verName].nameVer_)
        self.versions_[verName].libPath_ = ""
        
    def hasVersion(self, version):
        return version in self.versions_
    
    def getVersions(self):
        return sorted(self.versions_.keys())
    
    def getLocalDir(self, version):
        if self.hasVersion(version):
            return self.versions_[version].bPaths_.local_dir
        raise Exception("Error in getLocalDir" + self.name_ + " doesn't have version " + str(version))
    
    def getBuildSubDir(self, version):
        if self.hasVersion(version):
            return self.versions_[version].bPaths_.build_sub_dir
        raise Exception("Error in getBuildSubDir" + self.name_ + " doesn't have version " + str(version))
    
    def getBuildDir(self, version):
        if self.hasVersion(version):
            return self.versions_[version].bPaths_.build_dir
        raise Exception("Error in getBuildDir" + self.name_ + " doesn't have version " + str(version))
    
    def getGitRefs(self, url):
        if not self.libType_.startswith("git"):
            raise Exception("Library " + self.name_ + " is not a git library, type is : " + self.libType_)
        cap = Utils.runAndCapture("git ls-remote {url}".format(url = url))
        branches = []
        tags = []
        for line in cap.split("\n"):
            if "" != line:
                lineSplit = line.split()
                if 2 == len(lineSplit):
                    if "heads" in lineSplit[1]:
                        branches.append(lineSplit[1][(lineSplit[1].find("heads/") + 6):])
                    elif "tags" in lineSplit[1] and not lineSplit[1].endswith("^{}"):
                        tags.append(lineSplit[1][(lineSplit[1].find("tags/") + 5):])
        gRefs = GitRefs(branches, tags)
        return (gRefs)
            

class Packages():
    '''class to hold and setup all the necessary paths for 
    downloading, building, and then installing packages/libraries'''
    def __init__(self, externalLoc, args):
        self.dirMaster_ = LibDirMaster(externalLoc); #top dir to hold tars,build, local directories
        self.args = args
        self.packages_ = {} #dictionary to hold path infos
        self.packages_["zi_lib"] = self.__zi_lib()
        self.packages_["pstreams"] = self.__pstreams()
        self.packages_["cppitertools"] = self.__cppitertools()
        self.packages_["cppprogutils"] = self.__cppprogutils()
        self.packages_["boost"] = self.__boost()
        self.packages_["r"] = self.__r()
        self.packages_["cppcms"] = self.__cppcms()
        self.packages_["bamtools"] = self.__bamtools()
        self.packages_["jsoncpp"] = self.__jsoncpp()
        self.packages_["armadillo"] = self.__armadillo()
        self.packages_["bibseq"] = self.__bibseq()
        self.packages_["bibcpp"] = self.__bibcpp()
        self.packages_["seekdeep"] = self.__SeekDeep()
        self.packages_["bibseqdev"] = self.__bibseqDev()
        self.packages_["seekdeepdev"] = self.__SeekDeepDev()
        self.packages_["seqserver"] = self.__seqserver()
        self.packages_["njhrinside"] = self.__njhRInside()
        self.packages_["twobit"] = self.__twobit()
        self.packages_["sharedmutex"] = self.__sharedMutex()
        self.packages_["dlib"] = self.__dlib()
        self.packages_["libsvm"] = self.__libsvm()
        self.packages_["mongoc"] = self.__mongoc()
        self.packages_["mongocxx"] = self.__mongocxx()
        self.packages_["catch"] = self.__catch()
        self.packages_["mathgl"] = self.__mathgl()
        self.packages_["magic"] = self.__magic()
        '''
        self.packages_["mlpack"] = self.__mlpack()
        self.packages_["liblinear"] = self.__liblinear()
        '''

    def package(self, name):
        '''get package info if it exists'''
        if name in self.packages_:
            return self.packages_[name]
        raise Exception(name + " not found in paths")

    def __zi_lib(self):
        name = "zi_lib"
        url = 'https://github.com/weng-lab/zi_lib.git'
        buildCmd = ""
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git-headeronly", "master")
        if self.args.noInternet:
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                pack = pickle.load(input)
                pack.defaultBuildCmd_ = buildCmd
        elif os.path.exists(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl')):
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                    pack = pickle.load(input)
                    pack.defaultBuildCmd_ = buildCmd
        else:
            
            refs = pack.getGitRefs(url)
            for ref in [b.replace("/", "__") for b in refs.branches] + refs.tags:
                pack.addHeaderOnlyVersion(url, ref)
                pack.versions_[ref].includePath_ = os.path.join(name, ref, name)
                if not Utils.isMac():
                    pack.versions_[ref].additionalLdFlags_ = ["-lrt"]
            Utils.mkdir(os.path.join(self.dirMaster_.cache_dir, name))
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'wb') as output:
                pickle.dump(pack, output, pickle.HIGHEST_PROTOCOL)
        return pack
    
    def __pstreams(self):
        name = "pstreams"
        url = 'https://github.com/nickjhathaway/pstreams.git'
        buildCmd = ""
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git-headeronly", "RELEASE_0_8_1")
        if self.args.noInternet:
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                pack = pickle.load(input)
                pack.defaultBuildCmd_ = buildCmd
        elif os.path.exists(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl')):
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                    pack = pickle.load(input)
                    pack.defaultBuildCmd_ = buildCmd
        else:
            refs = pack.getGitRefs(url)
            for ref in [b.replace("/", "__") for b in refs.branches] + refs.tags:
                pack.addHeaderOnlyVersion(url, ref)
            Utils.mkdir(os.path.join(self.dirMaster_.cache_dir, name))
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'wb') as output:
                pickle.dump(pack, output, pickle.HIGHEST_PROTOCOL)
        return pack

    def __bamtools(self):
        url = 'https://github.com/nickjhathaway/bamtools.git'
        name = "bamtools"
        buildCmd = "mkdir -p build && cd build && CC={CC} CXX={CXX} cmake -DCMAKE_INSTALL_PREFIX:PATH={local_dir} .. && make -j {num_cores} install"
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git", "v2.4.0")
        if self.args.noInternet:
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                pack = pickle.load(input)
                pack.defaultBuildCmd_ = buildCmd
        elif os.path.exists(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl')):
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                    pack = pickle.load(input)
                    pack.defaultBuildCmd_ = buildCmd
        else:
            refs = pack.getGitRefs(url)
            for ref in [b.replace("/", "__") for b in refs.branches] + refs.tags:
                pack.addVersion(url, ref)
                pack.versions_[ref].libPath_ = os.path.join(pack.versions_[ref].libPath_,name)
                pack.versions_[ref].includePath_ = os.path.join(pack.versions_[ref].includePath_,name)
            Utils.mkdir(os.path.join(self.dirMaster_.cache_dir, name))
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'wb') as output:
                pickle.dump(pack, output, pickle.HIGHEST_PROTOCOL)
        return pack
    
    def __jsoncpp(self):
        url = "https://github.com/open-source-parsers/jsoncpp.git"
        name = "jsoncpp"
        buildCmd = "mkdir -p build && cd build && CC={CC} CXX={CXX} cmake -DCMAKE_CXX_FLAGS=-fPIC -DCMAKE_EXE_LINKER_FLAGS=-fPIC -DCMAKE_INSTALL_PREFIX:PATH={local_dir} ..  && make -j {num_cores} install"
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git", "1.7.1")
        if self.args.noInternet:
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                pack = pickle.load(input)
                pack.defaultBuildCmd_ = buildCmd
        elif os.path.exists(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl')):
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                    pack = pickle.load(input)
                    pack.defaultBuildCmd_ = buildCmd
        else:
            refs = pack.getGitRefs(url)
            for ref in [b.replace("/", "__") for b in refs.branches] + refs.tags:
                pack.addVersion(url, ref)
            Utils.mkdir(os.path.join(self.dirMaster_.cache_dir, name))
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'wb') as output:
                pickle.dump(pack, output, pickle.HIGHEST_PROTOCOL)
        return pack
    
    def __mongoc(self):
        url = "https://github.com/mongodb/mongo-c-driver.git"
        name = "mongoc"
        if Utils.isMac():
            buildCmd = "sed -i.bak s/git:/http:/g .gitmodules && CC={CC} CXX={CXX}  PKG_CONFIG_PATH=/usr/local/opt/openssl/lib/pkgconfig:$PKG_CONFIG_PATH ./autogen.sh --enable-ssl --enable-sasl --prefix={local_dir}&& make -j {num_cores}  && make install"
        else:
            buildCmd = "sed -i.bak s/git:/http:/g .gitmodules && CC={CC} CXX={CXX} ./autogen.sh --enable-ssl --enable-sasl --prefix={local_dir} && make -j {num_cores}  && make install"
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git", "1.3.3")
        pack.addVersion(url, "1.3.3")
        pack.versions_["1.3.3"].additionalIncludePaths_.append(pack.versions_["1.3.3"].includePath_ + "/libmongoc-1.0")
        pack.versions_["1.3.3"].includePath_ = pack.versions_["1.3.3"].includePath_ + "/libbson-1.0"
        pack.versions_["1.3.3"].altLibName_ = "ssl" #a trick to control order of -l flags for libs
        pack.versions_["1.3.3"].additionalLdFlags_ = ["-lcrypto","-lmongoc-1.0", "-lbson-1.0"]  
        if not Utils.isMac():
            pack.versions_["1.3.3"].additionalLdFlags_.append("-lrt") 
        pack.addVersion(url, "1.3.4")
        pack.versions_["1.3.4"].additionalIncludePaths_.append(pack.versions_["1.3.4"].includePath_ + "/libmongoc-1.0")
        pack.versions_["1.3.4"].includePath_ = pack.versions_["1.3.4"].includePath_ + "/libbson-1.0"
        pack.versions_["1.3.4"].altLibName_ = "ssl" #a trick to control order of -l flags for libs
        pack.versions_["1.3.4"].additionalLdFlags_ = ["-lcrypto","-lmongoc-1.0", "-lbson-1.0"]  
        if not Utils.isMac():
            pack.versions_["1.3.4"].additionalLdFlags_.append("-lrt") 
        return pack
    
    def __mongocxx(self):
        url = "https://github.com/mongodb/mongo-cxx-driver.git"
        name = "mongocxx"
        buildCmd = "cd build && PKG_CONFIG_PATH={external}/local/mongoc/{mongoc_ver}/mongoc/lib/pkgconfig/:PKG_CONFIG_PATH CC={CC} CXX={CXX} cmake -DCMAKE_BUILD_TYPE=Release -DLIBBSON_DIR={external}/local/mongoc/{mongoc_ver}/mongoc/ -DLIBMONGOC_DIR={external}/local/mongoc/{mongoc_ver}/mongoc/ -DCMAKE_INSTALL_PREFIX={local_dir} .. && make -j {num_cores} && make install"
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git", "r3.0.1")
        pack.addVersion(url, "r3.0.0", [LibNameVer("mongoc", "1.3.3")])
        pack.versions_["r3.0.0"].additionalIncludePaths_.append(pack.versions_["r3.0.0"].includePath_ + "/mongocxx/v_noabi")
        pack.versions_["r3.0.0"].includePath_ = pack.versions_["r3.0.0"].includePath_ + "/bsoncxx/v_noabi"
        pack.versions_["r3.0.0"].additionalLdFlags_ = ["-lbsoncxx"] 
        pack.addVersion(url, "r3.0.1", [LibNameVer("mongoc", "1.3.4")])
        pack.versions_["r3.0.1"].additionalIncludePaths_.append(pack.versions_["r3.0.1"].includePath_ + "/mongocxx/v_noabi")
        pack.versions_["r3.0.1"].includePath_ = pack.versions_["r3.0.1"].includePath_ + "/bsoncxx/v_noabi"
        pack.versions_["r3.0.1"].additionalLdFlags_ = ["-lbsoncxx"]
        return pack

    def __cppitertools(self):
        url = 'https://github.com/ryanhaining/cppitertools.git'
        name = "cppitertools"
        buildCmd = ""
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git-headeronly", "v0.1")
        if self.args.noInternet:
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                pack = pickle.load(input)
                pack.defaultBuildCmd_ = buildCmd
        elif os.path.exists(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl')):
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                    pack = pickle.load(input)
                    pack.defaultBuildCmd_ = buildCmd
        else:
            refs = pack.getGitRefs(url)
            for ref in [b.replace("/", "__") for b in refs.branches] + refs.tags:
                pack.addHeaderOnlyVersion(url, ref)
            Utils.mkdir(os.path.join(self.dirMaster_.cache_dir, name))
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'wb') as output:
                pickle.dump(pack, output, pickle.HIGHEST_PROTOCOL)
        return pack

    def __catch(self):
        url = 'https://github.com/philsquared/Catch.git'
        name = "catch"
        buildCmd = ""
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git-headeronly", "v1.3.3")
        if self.args.noInternet:
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                pack = pickle.load(input)
                pack.defaultBuildCmd_ = buildCmd
        elif os.path.exists(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl')):
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                    pack = pickle.load(input)
                    pack.defaultBuildCmd_ = buildCmd
        else:
            refs = pack.getGitRefs(url)
            for ref in [b.replace("/", "__") for b in refs.branches] + refs.tags:
                pack.addHeaderOnlyVersion(url, ref)
                pack.versions_[ref].includePath_ = os.path.join(joinNameVer(pack.versions_[ref].nameVer_), "single_include")
            Utils.mkdir(os.path.join(self.dirMaster_.cache_dir, name))
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'wb') as output:
                pickle.dump(pack, output, pickle.HIGHEST_PROTOCOL)
        return pack

    def __r(self):
        name = "R"
        rHomeLoc = "bin/R RHOME"
        if Utils.isMac():
            rHomeLoc = "R.framework/Resources/bin/R RHOME"
        #&& echo 'install.packages(c(\"gridExtra\", \"ape\", \"ggplot2\", \"seqinr\",\"Rcpp\", \"RInside\",\"devtools\"),
        buildCmd = """./configure --prefix={local_dir} --enable-R-shlib --with-x=no CC={CC} CXX={CXX} OBJC={CC}
                && make -j {num_cores}
                && make install
                && echo 'install.packages(c(\"gridExtra\", \"ape\", \"ggplot2\", \"seqinr\",\"Rcpp\", \"RInside\"),
                repos=\"http://cran.us.r-project.org\", Ncpus = {num_cores}, lib =.libPaths()[length(.libPaths()  )])' | $({local_dir}/""" + rHomeLoc + """)/bin/R --slave --vanilla
                """
        buildCmd = " ".join(buildCmd.split())
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "file", "3.2.4")
        pack.versions_["3.2.4"] = CPPLibPackageVersionR("R", "http://baileylab.umassmed.edu/sourceCodes/R/R-3.2.4.tar.gz", "3.2.4", self.dirMaster_)
        pack.versions_["3.2.3"] = CPPLibPackageVersionR("R", "http://baileylab.umassmed.edu/sourceCodes/R/R-3.2.3.tar.gz", "3.2.3", self.dirMaster_)
        pack.versions_["3.2.2"] = CPPLibPackageVersionR("R", "http://baileylab.umassmed.edu/sourceCodes/R/R-3.2.2.tar.gz", "3.2.2", self.dirMaster_)
        pack.versions_["3.2.1"] = CPPLibPackageVersionR("R", "http://baileylab.umassmed.edu/sourceCodes/R/R-3.2.1.tar.gz", "3.2.1", self.dirMaster_)
        pack.versions_["3.2.0"] = CPPLibPackageVersionR("R", "http://baileylab.umassmed.edu/sourceCodes/R/R-3.2.0.tar.gz", "3.2.0", self.dirMaster_)
        pack.versions_["3.1.3"] = CPPLibPackageVersionR("R", "http://baileylab.umassmed.edu/sourceCodes/R/R-3.2.2.tar.gz", "3.1.3", self.dirMaster_)
        return pack

    def __armadillo(self):
        name = "armadillo"
        buildCmd = "mkdir -p build && cd build && CC={CC} CXX={CXX} cmake -DCMAKE_INSTALL_PREFIX:PATH={local_dir} .. && make -j {num_cores} install"
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "file", "6.200.3")
        pack.addVersion("http://baileylab.umassmed.edu/sourceCodes/armadillo/armadillo-6.700.3.tar.gz", "6.700.3")
        pack.addVersion("http://baileylab.umassmed.edu/sourceCodes/armadillo/armadillo-6.200.3.tar.gz", "6.200.3")
        pack.addVersion("http://baileylab.umassmed.edu/sourceCodes/armadillo/armadillo-6.100.0.tar.gz", "6.100.0")
        pack.addVersion("http://baileylab.umassmed.edu/sourceCodes/armadillo/armadillo-5.600.2.tar.gz", "5.600.2")
        return pack
    '''
    def __mlpack(self):
        url = "http://www.mlpack.org/files/mlpack-1.0.8.tar.gz"
        armadillo_dir = Utils.shellquote(i.local_dir).replace("mlpack", "armadillo")
        boost_dir = Utils.shellquote(i.local_dir).replace("mlpack", "boost")
        cmd = """
        mkdir -p build
        && cd build
        && CC={CC} CXX={CXX} cmake -D DEBUG=OFF -D PROFILE=OFF
         -D ARMADILLO_LIBRARY={armadillo_dir}/lib/libarmadillo.so.4.0.2
         -D ARMADILLO_INCLUDE_DIR={armadillo_dir}/include/
         -D CMAKE_INSTALL_PREFIX:PATH={local_dir} ..
         -DBoost_NO_SYSTEM_PATHS=TRUE -DBOOST_INCLUDEDIR={boost}/include/ -DBOOST_LIBRARYDIR={boost}/lib/
        && make -j {num_cores} install
        """.format(local_dir=Utils.shellquote(i.local_dir),
           armadillo_dir=armadillo_dir,
           num_cores=self.num_cores(),
           boost=boost_dir, CC=self.CC, CXX=self.CXX)
        cmd = " ".join(cmd.split('\n'))
        return self.__package_dirs(url, "mlpack")
    
    def __liblinear(self):
        name = "liblinear"
        url = "http://www.csie.ntu.edu.tw/~cjlin/liblinear/oldfiles/liblinear-1.94.tar.gz"
        cmd = """
            perl -p -i -e 's/if\(check_probability_model/if\(1 || check_probability_model/' linear.cpp &&
            make &&
            mkdir -p {local_dir} &&
            cp predict train {local_dir} &&
            make lib &&
            cp linear.h liblinear.so.1 README {local_dir} &&
            ln -s {local_dir}/liblinear.so.1 {local_dir}/liblinear.so
            """.format(local_dir=Utils.shellquote(i.local_dir))
        cmd = " ".join(cmd.split())
        return self.__package_dirs(url, "liblinear")
    '''
    
    def __magic(self):
        name = "magic"
        buildCmd = """./configure CC={CC} CXX={CXX} --disable-dependency-tracking  --disable-silent-rules
            --prefix={local_dir}
            --enable-fsect-man5  --enable-static 
            && make -j {num_cores} 
            && make -j {num_cores} install"""
        buildCmd = " ".join(buildCmd.split())
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "file", "5.25")
        pack.addVersion("http://baileylab.umassmed.edu/sourceCodes/libmagic/file-5.25.tar.gz", "5.25")
        return pack
    
    def __mathgl(self):
        name = "mathgl"
        buildCmd = ""
        if "clang" in self.args.CC:
            buildCmd = """mkdir -p build && cd build && CC={CC} CXX={CXX} cmake -DCMAKE_INSTALL_PREFIX:PATH={local_dir} -Denable-pthread=ON -Denable-openmp=OFF .. 
            && make -j {num_cores} install"""
        else:
            buildCmd = """mkdir -p build && cd build && CC={CC} CXX={CXX} cmake -DCMAKE_INSTALL_PREFIX:PATH={local_dir}  .. 
            && make -j {num_cores} install"""
        buildCmd = " ".join(buildCmd.split())
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "file", "2.2.1")
        pack.addVersion("http://baileylab.umassmed.edu/sourceCodes/mathgl/mathgl-2.2.1.tar.gz", "2.2.1")
        pack.versions_["2.2.1"].includePath_ = os.path.join(pack.versions_["2.2.1"].includePath_,"mgl2")
        pack.versions_["2.2.1"].altLibName_ = "mgl"
        pack.addVersion("http://baileylab.umassmed.edu/sourceCodes/mathgl/mathgl-2.3.4.tar.gz", "2.3.4")
        pack.versions_["2.3.4"].includePath_ = os.path.join(pack.versions_["2.3.4"].includePath_,"mgl2")
        pack.versions_["2.3.4"].altLibName_ = "mgl"
        return pack
    
    def __cppcms(self):
        name = "cppcms"
        buildCmd = "mkdir -p build && cd build && CC={CC} CXX={CXX} cmake -DCMAKE_INSTALL_PREFIX:PATH={local_dir} .. && make -j {num_cores} install"
        if(sys.platform == "darwin"):
            buildCmd += " && install_name_tool -change libbooster.0.dylib {local_dir}/lib/libbooster.0.dylib {local_dir}/lib/libcppcms.1.dylib"
        buildCmd = " ".join(buildCmd.split())
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "file", "1.0.5")
        pack.addVersion("http://baileylab.umassmed.edu/sourceCodes/cppcms/cppcms-1.0.5.tar.bz2", "1.0.5")
        pack.versions_["1.0.5"].additionalLdFlags_ = ["-lbooster"]
        return pack

    def __dlib(self):
        name = "dlib"
        buildCmd = "mkdir {local_dir} && cp -a * {local_dir}/"
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "file", "18.7")
        pack.addVersion("http://freefr.dl.sourceforge.net/project/dclib/dlib/v18.7/dlib-18.7.tar.bz2", "18.7")
        pack.versions_["18.7"].includePath_ = joinNameVer(pack.versions_["18.7"].nameVer_)
        pack.versions_["18.7"].libPath_ = ""
        return pack
    
    def __libsvm(self):
        name = "libsvm"
        buildCmd = "make && make lib && mkdir -p {local_dir} && cp -a * {local_dir}"
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "file", "3.18")
        pack.addVersion("http://www.csie.ntu.edu.tw/~cjlin/libsvm/oldfiles/libsvm-3.18.tar.gz", "3.18")
        pack.versions_["3.18"].includePath_ = joinNameVer(pack.versions_["3.18"].nameVer_)
        pack.versions_["3.18"].libPath_ = ""
        return pack
    
    def __cppprogutils(self):
        url = 'https://github.com/bailey-lab/cppprogutils.git'
        name = "cppprogutils"
        buildCmd = ""
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git-headeronly", "v2.0.0")
        #pack.bibProject_ = True
        if self.args.noInternet:
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                pack = pickle.load(input)
                pack.defaultBuildCmd_ = buildCmd
        elif os.path.exists(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl')):
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                    pack = pickle.load(input)
                    pack.defaultBuildCmd_ = buildCmd
        else:
            refs = pack.getGitRefs(url)
            for ref in [b.replace("/", "__") for b in refs.branches] + refs.tags:
                pack.addHeaderOnlyVersion(url, ref)
                pack.versions_[ref].additionalLdFlags_ = ["-lpthread"]
                pack.versions_[ref].includePath_ = os.path.join(name, ref, name)
            Utils.mkdir(os.path.join(self.dirMaster_.cache_dir, name))
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'wb') as output:
                pickle.dump(pack, output, pickle.HIGHEST_PROTOCOL)
        return pack
    
    def __bibseq(self):
        url = "https://github.com/bailey-lab/bibseq.git"
        name = "bibseq"
        buildCmd = self.__bibProjectBuildCmd()
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git", "v2.3.0")
        pack.bibProject_ = True
        if self.args.noInternet:
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                pack = pickle.load(input)
                pack.defaultBuildCmd_ = buildCmd
        elif os.path.exists(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl')):
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                    pack = pickle.load(input)
                    pack.defaultBuildCmd_ = buildCmd
        else:
            refs = pack.getGitRefs(url)
            for ref in [b.replace("/", "__") for b in refs.branches] + refs.tags:
                pack.addVersion(url, ref)
                pack.versions_[ref].additionalLdFlags_ = ["-lcurl"]
            Utils.mkdir(os.path.join(self.dirMaster_.cache_dir, name))
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'wb') as output:
                pickle.dump(pack, output, pickle.HIGHEST_PROTOCOL)
        return pack
    
    def __bibseqDev(self):
        url = "git@github.com:bailey-lab/bibseqPrivate.git"
        name = "bibseqDev"
        buildCmd = self.__bibProjectBuildCmd()
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git", "master")
        pack.bibProject_ = True
        try:
            if self.args.noInternet:
                with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                    pack = pickle.load(input)
                    pack.defaultBuildCmd_ = buildCmd
            elif os.path.exists(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl')):
                with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                        pack = pickle.load(input)
                        pack.defaultBuildCmd_ = buildCmd
            else:
                
                refs = pack.getGitRefs(url)
                for ref in [b.replace("/", "__") for b in refs.branches] + refs.tags:
                    pack.addVersion(url, ref)
                    pack.versions_[ref].additionalLdFlags_ = ["-lcurl"]
                Utils.mkdir(os.path.join(self.dirMaster_.cache_dir, name))
                with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'wb') as output:
                    pickle.dump(pack, output, pickle.HIGHEST_PROTOCOL)
        except Exception as inst: 
            print CT.boldRed("failed to update cache for ") + name + " which doesn't matter unless you are installing this lib"
        return pack 
    
    def __twobit(self):
        url = "https://github.com/weng-lab/TwoBit.git"
        name = "TwoBit"
        buildCmd = self.__bibProjectBuildCmd()
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git", "v2.0.1")
        pack.bibProject_ = True
        if self.args.noInternet:
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                pack = pickle.load(input)
                pack.defaultBuildCmd_ = buildCmd
        elif os.path.exists(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl')):
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                    pack = pickle.load(input)
                    pack.defaultBuildCmd_ = buildCmd
        else:
            refs = pack.getGitRefs(url)
            for ref in [b.replace("/", "__") for b in refs.branches] + refs.tags:
                pack.addVersion(url, ref)
            Utils.mkdir(os.path.join(self.dirMaster_.cache_dir, name))
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'wb') as output:
                pickle.dump(pack, output, pickle.HIGHEST_PROTOCOL)
        return pack
    
    def __sharedMutex(self):
        url = "https://github.com/nickjhathaway/cpp_shared_mutex.git"
        name = "sharedMutex"
        buildCmd = self.__bibProjectBuildCmd()
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git", "v0.3")
        pack.bibProject_ = True
        if self.args.noInternet:
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                pack = pickle.load(input)
                pack.defaultBuildCmd_ = buildCmd
        elif os.path.exists(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl')):
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                    pack = pickle.load(input)
                    pack.defaultBuildCmd_ = buildCmd
        else:
            refs = pack.getGitRefs(url)
            for ref in [b.replace("/", "__") for b in refs.branches] + refs.tags:
                pack.addVersion(url, ref)
            Utils.mkdir(os.path.join(self.dirMaster_.cache_dir, name))
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'wb') as output:
                pickle.dump(pack, output, pickle.HIGHEST_PROTOCOL)
        return pack 
      
    def __SeekDeep(self):
        url = "https://github.com/bailey-lab/SeekDeep.git"
        name = "SeekDeep"
        buildCmd = self.__bibProjectBuildCmd()
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git", "v2.3.3")
        pack.bibProject_ = True
        if self.args.noInternet:
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                pack = pickle.load(input)
                pack.defaultBuildCmd_ = buildCmd
        elif os.path.exists(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl')):
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                    pack = pickle.load(input)
                    pack.defaultBuildCmd_ = buildCmd
        else:
            refs = pack.getGitRefs(url)
            for ref in [b.replace("/", "__") for b in refs.branches] + refs.tags:
                pack.addVersion(url, ref)
            Utils.mkdir(os.path.join(self.dirMaster_.cache_dir, name))
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'wb') as output:
                pickle.dump(pack, output, pickle.HIGHEST_PROTOCOL)
        return pack
    
    def __SeekDeepDev(self):
        url = "git@github.com:bailey-lab/SeekDeepPrivate.git"
        name = "SeekDeepDev"
        buildCmd = self.__bibProjectBuildCmd()
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git", "master")
        pack.bibProject_ = True
        try:
            if self.args.noInternet:
                with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                    pack = pickle.load(input)
                    pack.defaultBuildCmd_ = buildCmd
            elif os.path.exists(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl')):
                with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                        pack = pickle.load(input)
                        pack.defaultBuildCmd_ = buildCmd
            else:
                refs = pack.getGitRefs(url)
                for ref in [b.replace("/", "__") for b in refs.branches] + refs.tags:
                    pack.addVersion(url, ref)
                Utils.mkdir(os.path.join(self.dirMaster_.cache_dir, name))
                with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'wb') as output:
                    pickle.dump(pack, output, pickle.HIGHEST_PROTOCOL)
        except Exception as inst:
            print inst 
            print CT.boldRed("failed to update cache for ") + name + " which doesn't matter unless you are installing this lib"
        return pack
    
    def __seqserver(self):
        url = "https://github.com/nickjhathaway/seqServer.git"
        name = "seqServer"
        buildCmd = self.__bibProjectBuildCmd()
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git", "v1.3.1")
        pack.bibProject_ = True
        if self.args.noInternet:
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                pack = pickle.load(input)
                pack.defaultBuildCmd_ = buildCmd
        elif os.path.exists(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl')):
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                    pack = pickle.load(input)
                    pack.defaultBuildCmd_ = buildCmd
        else:
            refs = pack.getGitRefs(url)
            for ref in [b.replace("/", "__") for b in refs.branches] + refs.tags:
                pack.addVersion(url, ref)
            Utils.mkdir(os.path.join(self.dirMaster_.cache_dir, name))
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'wb') as output:
                pickle.dump(pack, output, pickle.HIGHEST_PROTOCOL)
        return pack
    
    def __njhRInside(self):
        url = "https://github.com/nickjhathaway/njhRInside.git"
        name = "njhRInside"
        buildCmd = self.__bibProjectBuildCmd()
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git", "1.1.1")
        pack.bibProject_ = True
        if self.args.noInternet:
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                pack = pickle.load(input)
                pack.defaultBuildCmd_ = buildCmd
        elif os.path.exists(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl')):
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                    pack = pickle.load(input)
                    pack.defaultBuildCmd_ = buildCmd
        else:
            refs = pack.getGitRefs(url)
            for ref in [b.replace("/", "__") for b in refs.branches] + refs.tags:
                pack.addVersion(url, ref)
            Utils.mkdir(os.path.join(self.dirMaster_.cache_dir, name))
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'wb') as output:
                pickle.dump(pack, output, pickle.HIGHEST_PROTOCOL)
        return pack
    
    def __bibcpp(self):
        url = "https://github.com/umass-bib/bibcpp.git"
        name = "bibcpp"
        buildCmd = self.__bibProjectBuildCmd()
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git", "v2.3.0")
        pack.bibProject_ = True
        if self.args.noInternet:
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                pack = pickle.load(input)
                pack.defaultBuildCmd_ = buildCmd
        elif os.path.exists(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl')):
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'rb') as input:
                    pack = pickle.load(input)
                    pack.defaultBuildCmd_ = buildCmd
        else:
            refs = pack.getGitRefs(url)
            for ref in [b.replace("/", "__") for b in refs.branches] + refs.tags:
                pack.addVersion(url, ref)
                pack.versions_[ref].additionalLdFlags_ = ["-lpthread", "-lz"]
                if not Utils.isMac():
                    pack.versions_[ref].additionalLdFlags_.append("-lrt")
            Utils.mkdir(os.path.join(self.dirMaster_.cache_dir, name))
            with open(os.path.join(self.dirMaster_.cache_dir, name, name + '.pkl'), 'wb') as output:
                pickle.dump(pack, output, pickle.HIGHEST_PROTOCOL)
        return pack

    def __boost(self):
        name = "boost"
        buildCmd = ""
        boostLibs = "filesystem,system"
        if Utils.isMac():
            #print "here"
            setUpDir = os.path.dirname(os.path.abspath(__file__))
            gccJamLoc =  os.path.join(setUpDir, "scripts/etc/boost/gcc.jam")
            gccJamOutLoc = "{build_sub_dir}/tools/build/src/tools/gcc.jam"
            #print gccJamLoc
            #print gccJamOutLoc
            installNameToolCmd  = """ 
            && install_name_tool -change $(otool -L {local_dir}/lib/libboost_filesystem.dylib | egrep -o "\\S.*libboost_system.dylib") {local_dir}/lib/libboost_system.dylib {local_dir}/lib/libboost_filesystem.dylib
            && install_name_tool -id {local_dir}/lib/libboost_filesystem.dylib {local_dir}/lib/libboost_filesystem.dylib
            && install_name_tool -id {local_dir}/lib/libboost_system.dylib {local_dir}/lib/libboost_system.dylib
            """
        if self.args.clang:
            if Utils.isMac():
                buildCmd = """./bootstrap.sh --with-toolset=clang --prefix={local_dir} --with-libraries=""" + boostLibs + """
                  &&  ./b2  toolset=clang cxxflags=\"-stdlib=libc++ -std=c++14\" linkflags=\"-stdlib=libc++\" -j {num_cores} install 
                  &&  install_name_tool -change libboost_system.dylib {local_dir}/lib/libboost_system.dylib {local_dir}/lib/libboost_filesystem.dylib
                  """
            else:
                buildCmd = """ln -s $(for x in $(which -a {CC}); do echo $(realpath $x); done | egrep clang | head -1) clang && PATH=$(realpath .):$PATH && ln -s $(for x in $(which -a {CXX}); do echo $(realpath $x); done | egrep clang | head -1) clang++ && ./bootstrap.sh --with-toolset=clang --prefix={local_dir}  --with-libraries=""" + boostLibs + """ &&  ./b2 toolset=clang cxxflags=\"-std=c++14\" -j {num_cores} install && rm clang && rm clang++"""
        elif "g++" in self.args.CXX:
            if "-" in self.args.CXX:
                gccVer = self.args.CXX[(self.args.CXX.find("-") + 1):]
                if Utils.isMac():
                    buildCmd = "cp " + gccJamLoc + "  " + gccJamOutLoc + """ && echo "using gcc : """ + str(gccVer) + """ : {CXX} : <linker-type>darwin ;" >> project-config.jam 
                     && ./bootstrap.sh --with-toolset=gcc --prefix={local_dir} --with-libraries=""" + boostLibs + """
                     && ./b2 --toolset=gcc-""" + str(gccVer) +  """ -j {num_cores} install 
                     """ + installNameToolCmd
                else:
                    buildCmd = """echo "using gcc : """ + str(gccVer) + """ : {CXX};" >> project-config.jam && ./bootstrap.sh --with-toolset=gcc --prefix={local_dir} --with-libraries=""" + boostLibs + """
                     && ./b2 --toolset=gcc-""" + str(gccVer) +  """ -j {num_cores} install 
                     """
            else:
                if Utils.isMac():
                    buildCmd = "cp " + gccJamLoc + "  " + gccJamOutLoc + """ && echo "using gcc :  : g++ : <linker-type>darwin ;" >> project-config.jam 
                     && ./bootstrap.sh --with-toolset=gcc --prefix={local_dir} --with-libraries=""" + boostLibs + """
                     && ./b2 --toolset=gcc -j {num_cores} install 
                     """ + installNameToolCmd
                else:
                    buildCmd = """echo "using gcc : : g++;" >> project-config.jam && ./bootstrap.sh --with-toolset=gcc --prefix={local_dir} --with-libraries=""" + boostLibs + """
                     && ./b2 --toolset=gcc -j {num_cores} install 
                     """
        buildCmd = " ".join(buildCmd.split())
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "file", "1_60_0")
        pack.addVersion("http://baileylab.umassmed.edu/sourceCodes/boost/boost_1_58_0.tar.bz2", "1_58_0")
        pack.versions_["1_58_0"].additionalLdFlags_ = ["-lboost_system", "-lboost_filesystem"]
        pack.versions_["1_58_0"].libName_ = ""
        pack.addVersion("http://baileylab.umassmed.edu/sourceCodes/boost/boost_1_59_0.tar.bz2", "1_59_0")
        pack.versions_["1_59_0"].additionalLdFlags_ = ["-lboost_system", "-lboost_filesystem"]
        pack.versions_["1_59_0"].libName_ = ""
        pack.addVersion("http://baileylab.umassmed.edu/sourceCodes/boost/boost_1_60_0.tar.bz2", "1_60_0")
        pack.versions_["1_60_0"].additionalLdFlags_ = ["-lboost_system", "-lboost_filesystem"]
        pack.versions_["1_60_0"].libName_ = ""
        return pack
    
    def getPackagesNames(self):
        return sorted(self.packages_.keys())
    
    def checkForPackVer(self, packVer):
        if packVer.name not in self.packages_:
            raise Exception("Lib " + packVer.name + " not found in libs, options are " + ", ".join(self.getPackagesNames()))
        else:
            if packVer.version.replace("/", "__") not in self.packages_[packVer.name].versions_:
                raise Exception("Version " + packVer.version + " for lib " \
                                + packVer.name + " not found in available versions, options are " \
                                + ", ".join(self.packages_[packVer.name].getVersions()))
        return True
                
    def getLdFlags(self, packVer):
        self.checkForPackVer(packVer)
        return self.packages_[packVer.name].versions_[packVer.version].getLdFlags(self.dirMaster_.install_dir)
    
    def getIncludeFlags(self, packVer):
        self.checkForPackVer(packVer)
        return self.packages_[packVer.name].versions_[packVer.version].getIncludeFlags(self.dirMaster_.install_dir)
    
    def writeMakefile(self, packVers, filename, overwrite = False, append = False):
        if os.path.exists(filename) and not overwrite and not append:
            raise Exception("File: " + str(filename) + " already exists, use --overWrite to overwrite it")
        elif os.path.exists(filename) and overwrite:
            os.remove(filename)
            self.writeMakefile(packVers, filename, overwrite, append)
        elif os.path.exists(filename) and append:
            with open(filename, "a") as f:
                for packVer in packVers:
                    pack = self.package(packVer.name)
                    #if bib project, add the flags of it's dependencies
                    if pack.bibProject_:
                        cmd = "python ./setup.py --compfile compfile.mk --numCores 1 --append --outMakefile {makefileCommon}".format(makefileCommon = os.path.abspath(filename))
                        dir = pack.getBuildSubDir(packVer.version)
                        Utils.run_in_dir(cmd, dir)
                    pvIncFlags = self.getIncludeFlags(packVer)
                    if "" != pvIncFlags:
                        f.write("#" + packVer.name + ":" + packVer.version + " CXXFLAGS\n")
                        f.write("COMLIBS += " + pvIncFlags + "\n")
                    pvLdFlags = self.getLdFlags(packVer)
                    if "" != pvLdFlags:
                        f.write("#" + packVer.name + ":" + packVer.version + " LDFLAGS\n")
                        f.write("LD_FLAGS += " + pvLdFlags + "\n")
                    f.write("\n")
                    f.flush()
        else:
            with open(filename, "a") as f:
                f.write("#Utils\n")
                f.write("# from http://stackoverflow.com/a/18258352\n")
                f.write("rwildcard=$(foreach d,$(wildcard $1*),$(call rwildcard,$d/,$2) $(filter $(subst *,%,$2),$d))\n")
                f.write("\n")
                f.write("#Default CXXFLAGS\n")
                f.write("COMLIBS += " + self.getDefaultIncludeFlags() + "\n")
                dLdFlags = self.getDefaultLDFlags( )
                if "" != dLdFlags:
                    f.write("#Default LDFLAGS\n")
                    f.write("LD_FLAGS += " + dLdFlags + "\n")
                f.write("\n")
                f.flush()
                for packVer in packVers:
                    pack = self.package(packVer.name)
                    #if bib project, add the flags of it's dependencies
                    if pack.bibProject_:
                            cmd = "python ./setup.py --compfile compfile.mk --numCores 1 --append --outMakefile {makefileCommon}".format(makefileCommon = os.path.abspath(filename))
                            dir = pack.getBuildSubDir(packVer.version)
                            Utils.run_in_dir(cmd, dir)
                    pvIncFlags = self.getIncludeFlags(packVer)
                    if "" != pvIncFlags:
                        f.write("#" + packVer.name + ":" + packVer.version + " CXXFLAGS\n")
                        f.write("COMLIBS += " + pvIncFlags + "\n")
                    pvLdFlags = self.getLdFlags(packVer)
                    if "" != pvLdFlags:
                        f.write("#" + packVer.name + ":" + packVer.version + " LDFLAGS\n")
                        f.write("LD_FLAGS += " + pvLdFlags + "\n")
                    f.write("\n")
                    f.flush()
    
    def addPackage(self, packVers, packVer):
        packVer = LibNameVer(packVer.name, packVer.version.replace("/", "__"))
        if self.checkForPackVer(packVer):
            pack = self.package(packVer.name)
            for dep in pack.versions_[packVer.version].depends_:
                self.addPackage(packVers, LibNameVer(str(dep.name).lower(), dep.version))
            found = False
            for otherPackVer in packVers:
                if otherPackVer.name == packVer.name:
                    if otherPackVer.version != packVer.version:
                        raise Exception("Version conflict for " + packVer.name + " already have " + otherPackVer.version + " and adding: " + packVer.version)
                    else:
                        found = True
            if not found:
                packVers.append(packVer)
            
                
                
    def isInstalled(self, packVer):
        if os.path.exists(os.path.join(self.dirMaster_.install_dir, joinNameVer(packVer))):
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

    def __bibProjectBuildCmdOld(self):
        cmd = """
        python ./configure.py -CC {CC} -CXX {CXX} -externalLibDir {external} -prefix {localTop} 
        && python ./setup.py --compfile compfile.mk --numCores {num_cores}
        && make -j {num_cores} && make install"""
        cmd = " ".join(cmd.split())
        return cmd
    
    def __bibProjectBuildCmd(self):
        cmd = """
        python ./configure.py -CC {CC} -CXX {CXX} -externalLibDir {external} -prefix $(dirname {local_dir}) """
        if self.args.noInternet:
            cmd = cmd + """&& python ./setup.py --compfile compfile.mk --numCores {num_cores}
             --outMakefile makefile-common.mk --overWrite --noInternet """
        else:
            cmd = cmd + """&& python ./setup.py --compfile compfile.mk --numCores {num_cores}
             --outMakefile makefile-common.mk --overWrite """
        cmd = cmd + """&& make clean
        && make -j {num_cores} && make install"""
        cmd = " ".join(cmd.split())
        return cmd
    
    
    
class Setup:
    def __init__(self, args):
        self.extDirLoc = "" # the location where the libraries will be installed
        #if no compile file set up and assume external is next to setup.py
        if not args.compfile:
            self.extDirLoc = "external"
            #self.extDirLoc = os.path.abspath(os.path.join(os.path.dirname(__file__), "external"))
        else:
            self.extDirLoc = os.path.abspath(self.parseForExtPath(args.compfile[0]))
        self.dirMaster_ = LibDirMaster(self.extDirLoc)
        self.args = args # command line arguments parsed by argument parser
        self.setUps = {} # all available set ups
        self.setUpsNeeded = [] # the setups that need to be done
        self.installed = [] # the setups that able to install
        self.failedInstall = [] # the setups that failed
        self.CC = "" # the c compilier being used
        self.CXX = "" # the c++ compilier being used
        self.noInternet_ = False
        if args.noInternet:
            self.noInternet_ = True
        self.__initSetUpFuncs()
        self.__processArgsForCompilers()
        #if we have internet and the cache is more than a day old, clear it
        if Utils.connectedInternet:
            cacheDate = datetime.datetime.fromtimestamp(os.path.getmtime(self.dirMaster_.cache_dir))
            now = datetime.datetime.now()
            if 86400 < (now - cacheDate).total_seconds():
                self.clearCache()
        if args.clearCache:
            self.clearCache()
        self.packages_ = Packages(self.extDirLoc, self.args) # path object to hold the paths for install
        self.__processArgsForSetupsNeeded()
        
    def setup(self):
        if self.args.forceUpdate:
            for set in self.setUpsNeeded:
                if not set.name in self.setUps.keys():
                    print CT.boldBlack( "Unrecognized option ") + CT.boldRed(set.name)
                else:
                    self.rmDirsForLib(set)
                    
        for set in self.setUpsNeeded:
            if not set.name in self.setUps.keys():
                print CT.boldBlack( "Unrecognized option ") + CT.boldRed(set.name)
            else:
                self.__setup(set.name, set.version)

        for p in self.installed:
            print p.name + ":" + str(p.version), CT.boldGreen("installed")

        for p in self.failedInstall:
            print  p.name + ":" + str(p.version), CT.boldRed("failed to install")

    def __initSetUpFuncs(self):
        self.setUps = {"zi_lib": self.zi_lib,
                       "boost": self.boost,
                       "cppitertools": self.cppitertools,
                       "catch": self.catch,
                       "cppprogutils": self.cppprogutils,
                       "r": self.r,
                       "bamtools": self.bamtools,
                       "cppcms": self.cppcms,
                       "armadillo": self.armadillo,
                       "bibseq": self.bibseq,
                       "seekdeep": self.SeekDeep,
                       "bibcpp": self.bibcpp,
                       "bibseqdev": self.bibseqDev,
                       "seekdeepdev": self.SeekDeepDev,
                       "seqserver": self.seqserver,
                       "njhrinside": self.njhRInside,
                       "jsoncpp": self.jsoncpp,
                       "pstreams": self.pstreams,
                       "dlib": self.dlib,
                       "libsvm": self.libsvm,
                       "mongoc": self.mongoc,
                       "mongocxx": self.mongocxx,
                       "twobit" : self.twobit,
                       "sharedmutex" : self.sharedMutex,
                       "mathgl": self.mathgl,
                       "magic": self.magic
                       }
        '''
        "mlpack": self.mlpack,
        "liblinear": self.liblinear,
        '''
    def printAvailableSetUps(self):
        self.__initSetUpFuncs()
        print "Available installs:"
        print "To Install use ./setup.py --libs lib1,lib2,lib3"
        print "E.g. ./setup.py --libs bamtools,boost"
        installs = self.setUps.keys()
        installs.sort()
        for set in installs:
            print set
            pack = self.__package(set)
            sys.stdout.write("\t")
            sys.stdout.write(",".join([p.replace("__", "/") for p in pack.getVersions()]))
            sys.stdout.write("\n")
            
    def printGitRefs(self):
        self.__initSetUpFuncs()
        print "Git branches and tags:"
        for set in self.setUpsNeeded:
            print set.name
            pack = self.__package(set.name)
            refs = pack.getGitRefs(pack.versions_[pack.defaultVersion_].bPaths_.url)
            print "\t" + "Branches"
            for b in refs.branches:
                print "\t\t" + b
            print "\t" + "Tags"
            for t in refs.tags:
                print "\t\t" + t

    def __processArgsForSetupsNeeded(self):
        if self.args.libs:
            inLibs = self.args.libs.split(",")
            for lib in inLibs:
                if ":" not in lib.lower():
                    raise Exception("Need to give version for " + lib)
                else:
                    libSplit = lib.split(":")
                    self.packages_.addPackage(self.setUpsNeeded,LibNameVer(libSplit[0].lower(), libSplit[1]))
        if self.args.compfile:
            self.parseSetUpNeeded(self.args.compfile[0])
    
    def __processArgsForCompilers(self):
        if self.args.compfile:
            self.parserForCompilers(self.args.compfile[0])
        # if no compfile need to determine compiler, will default to env CC and CXX
        else:
            self.CC = genHelper.determineCC(self.args)
            self.CXX = genHelper.determineCXX(self.args)
            self.args.CC = self.CC
            self.args.CXX = self.CXX
        if "clang" in self.CXX:
            self.args.clang = True
        else:
            self.args.clang = False

    def parseForExtPath(self, fn):
        args = self.parseCompFile(fn)
        if "EXT_PATH" in args:
            extPath = args["EXT_PATH"].strip()
            extPath = extPath.replace("$(realpath", "")
            extPath = extPath.replace(")", "")
            extPath = extPath.strip()
        else:
            print "did not find external folder location; assuming ./external"
            extPath = "./external"
        return extPath

    def parseSetUpNeeded(self, fn):
        args = self.parseCompFile(fn)
        for k,v in args.iteritems():
            if k.startswith("USE_"):
                if '0' != v:
                    if "#" in v:
                        valSplit = v.split("#")
                        if valSplit[0] == '1':
                            self.packages_.addPackage(self.setUpsNeeded, LibNameVer(k[4:].lower(),valSplit[1]))
                    else:
                        raise Exception("Need to supply version in compfile with USE_PACKAGE#Version")
                

    def parseCompFile(self, fn):
        ret = {}
        with open(fn) as f:
            for line in f:
                if '=' in line:
                    toks = line.split('=')
                    ret[toks[0].strip()] = toks[1].strip()
        return ret

    def parserForCompilers(self, fn):
        args = self.parseCompFile(fn)
        if 'CC' in args:
            self.CC = args['CC']
            self.args.CC = self.CC
        if 'CXX' in args:
            self.CXX = args['CXX']
            self.args.CXX = self.CXX
    
    def rmDirsForLibs(self,libs):
        for l in libs:
            self.rmDirsForLib(l)
    
    def rmDirsForLib(self,packVer):
        if packVer.name not in self.setUps:
            print CT.boldBlack( "Unrecognized package: ") + CT.boldRed(packVer.name)
        else:
            pack = self.__package(packVer.name)
            if not pack.hasVersion(packVer.version):
                raise Exception("No version " + str(packVer.version) + " for " + str(packVer.name))
            p = pack.versions_[packVer.version].bPaths_
            if os.path.exists(p.build_dir):
                print "Removing " + CT.boldBlack(p.build_dir)
                Utils.rm_rf(p.build_dir)
            if os.path.exists(p.local_dir):
                print "Removing " + CT.boldBlack(p.local_dir)
                Utils.rm_rf(p.local_dir)
    

    def __package(self, name):
        return self.packages_.package(name)

    def __setup(self, name, version):
        version = version.replace("/", "__")
        pack = self.__package(name)
        if not pack.hasVersion(version):
            raise Exception("Package " + str(name) + " doesn't have version " + str(version))
        bPath = pack.versions_[version].bPaths_
        if os.path.exists(bPath.local_dir):
            print CT.boldGreen(name + ":" + version), "found at " + CT.boldBlue(bPath.local_dir)
        else:
            print CT.boldGreen(name + ":" + version), CT.boldRed("NOT"), "found; building..."
            try:
                self.setUps[name](version)
                self.installed.append(LibNameVer(name, version))
            except Exception as inst:
                print inst 
                print CT.boldRed("failed to install ") + name + ":" + str(version)
                self.failedInstall.append(LibNameVer(name, version))

    def num_cores(self):
        retCores = Utils.num_cores()
        if self.args.numCores:
            if not self.args.numCores > retCores:
                retCores = self.args.numCores
        else:
            if retCores > 8:
                retCores  = retCores/2
            if 1 != retCores:
                retCores -= 1
        return retCores

    def __buildFromFile(self, packVer, cmd):
        bPath = packVer.bPaths_
        if self.noInternet_:
            newUrl = bPath.url.replace(".git","/archive/" + str(packVer.nameVer_.version) + ".tar.gz").replace("git@github.com:", "https://github.com/")
            bPath = BuildPaths(newUrl, bPath.build_dir, bPath.build_sub_dir, bPath.local_dir)
            base_file = os.path.basename(bPath.url)
            fnp = os.path.join(self.dirMaster_.ext_tars,packVer.nameVer_.name, base_file)
            if not os.path.exists(fnp):
                raise Exception("Could not find file: " + str(fnp))
        else:
            print "\t Getting file..."
            Utils.mkdir(os.path.join(self.dirMaster_.ext_tars, packVer.nameVer_.name))
            fnp = Utils.get_file_if_size_diff(bPath.url, os.path.join(self.dirMaster_.ext_tars, packVer.nameVer_.name))
        Utils.clear_dir(bPath.build_dir)
        Utils.untar(fnp, bPath.build_dir)
        ##probably not the best way to do this as there is no guarantee that there is a directory there
        untaredDir = os.listdir(bPath.build_dir)[0]
        os.rename(os.path.join(bPath.build_dir, untaredDir), bPath.build_sub_dir)
        try:
            Utils.run_in_dir(cmd, bPath.build_sub_dir)
        except:
            print "\t Failed to build, removing {d}".format(d = bPath.local_dir)
            Utils.rm_rf(bPath.local_dir)
            sys.exit(1)
                
    def __buildFromGitBranch(self, packVer, cmd):
        bPath = packVer.bPaths_
        if self.noInternet_:
            self.__buildFromFile(packVer, cmd)
        else:
            if os.path.exists(bPath.build_sub_dir):
                print "pulling from {url}".format(url=bPath.url)
                pCmd = "git checkout " + packVer.nameVer_.version.replace("__", "/") + " && git pull"
                try:
                    Utils.run_in_dir(pCmd, bPath.build_sub_dir)
                except:
                    print "failed to pull from {url} with {cmd}".format(url=bPath.url, cmd = pCmd)
                    sys.exit(1)
            else:
                print "cloning from {url}".format(url=bPath.url)
                cCmd = "git clone -b " + packVer.nameVer_.version.replace("__", "/") + " {url} {d}".format(url=bPath.url, d=bPath.build_sub_dir)
                try:
                    Utils.run(cCmd)
                except:
                    print "failed to clone from {url}".format(url=bPath.url)
                    sys.exit(1)
            try:
                Utils.run_in_dir(cmd, bPath.build_sub_dir)
            except:
                print("Failed to build, removing {d}".format(d = bPath.local_dir))
                Utils.rm_rf(bPath.local_dir)
                sys.exit(1)
    
    def __buildFromGitTag(self, packVer, cmd):
        bPath = packVer.bPaths_
        ##if no internet build from tar file, file needs to be in tarballs folder
        if self.noInternet_:
            self.__buildFromFile(packVer, cmd)
        else:
            if os.path.exists(bPath.build_sub_dir):
                print "pulling from {url}".format(url=bPath.url)
                pCmd = "git checkout master && git pull && git checkout " + packVer.nameVer_.version
                try:
                    Utils.run_in_dir(pCmd, bPath.build_sub_dir)
                except Exception, e:
                    print e
                    print "failed to pull from {url}".format(url=bPath.url)
                    sys.exit(1)
            else:
                print "cloning from {url}".format(url=bPath.url)
                cCmd = "git clone {url} {d}".format(url=bPath.url, d=bPath.build_sub_dir)
                tagCmd = "git checkout {tag}".format(tag=packVer.nameVer_.version)
                try:
                    Utils.run(cCmd)
                    Utils.run_in_dir(tagCmd, bPath.build_sub_dir)
                except Exception, e:
                    print e
                    print "failed to clone from {url}".format(url=bPath.url)
                    sys.exit(1)
            try:
                Utils.run_in_dir(cmd, bPath.build_sub_dir)
            except Exception, e:
                print e
                print "failed to build in {BUILD}, removing {LOCAL}".format(BUILD=bPath.build_sub_dir, LOCAL = bPath.local_dir)
                Utils.rm_rf(bPath.local_dir)
                sys.exit(1)
    
    def __gitBranch(self, packVer):
        bPath = packVer.bPaths_
        '''
            For header only libraries, will be put directly into local
        '''
        if self.noInternet_:
            newUrl = bPath.url.replace(".git","/archive/" + str(packVer.nameVer_.version) + ".tar.gz").replace("git@github.com:", "https://github.com/")
            base_file = os.path.basename(newUrl)
            fnp = os.path.join(self.dirMaster_.ext_tars,packVer.nameVer_.name, base_file)
            Utils.clear_dir(os.path.dirname(bPath.local_dir))
            Utils.untar(fnp, os.path.dirname(bPath.local_dir))
            ## might not be the best way to do this but works for now
            untaredDir = os.listdir(os.path.dirname(bPath.local_dir))[0]
            os.rename(os.path.join(os.path.dirname(bPath.local_dir), untaredDir), bPath.local_dir)
        else:
            print "cloning from {url}".format(url=bPath.url)
            cCmd = "git clone -b {branch} {url} {d}".format(branch = packVer.nameVer_.version.replace("__", "/"),url=bPath.url, d=bPath.local_dir)
            try:
                Utils.run(cCmd)
            except Exception, e:
                print e
                print "failed to clone branch {branch} from {url}".format(branch = packVer.nameVer_.version.replace("__", "/"), url=bPath.url)
                sys.exit(1)
    
    def __gitTag(self, packVer):
        bPath = packVer.bPaths_
        '''
            For header only libraries, will be put directly into local
        '''
        if self.noInternet_:
            newUrl = bPath.url.replace(".git","/archive/" + str(packVer.nameVer_.version) + ".tar.gz").replace("git@github.com:", "https://github.com/")
            base_file = os.path.basename(newUrl)
            fnp = os.path.join(self.dirMaster_.ext_tars,packVer.nameVer_.name, base_file)
            Utils.clear_dir(os.path.dirname(bPath.local_dir))
            Utils.untar(fnp, os.path.dirname(bPath.local_dir))
            ## might not be the best way to do this but works for now
            untaredDir = os.listdir(os.path.dirname(bPath.local_dir))[0]
            os.rename(os.path.join(os.path.dirname(bPath.local_dir), untaredDir), bPath.local_dir)
        else:
            cmd = "git clone {url} {d}".format(url=bPath.url, d=Utils.shellquote(bPath.local_dir))
            tagCmd = "git checkout {tag}".format(tag=packVer.nameVer_.version)
            try:
                Utils.run(cmd)
                Utils.run_in_dir(tagCmd, bPath.local_dir)
            except:
                print "failed to clone from {url}".format(url=bPath.url)
                sys.exit(1)
    
    def __defaultBuild(self, package, version, fromGitTag = True):
        pack = self.__package(package)
        if not pack.hasVersion(version):
            raise Exception("No set up for version " + str(version) + " for " + str(package))
        packVer = pack.versions_[version]
        bPaths = packVer.bPaths_
        cmd = pack.defaultBuildCmd_.format(external = Utils.shellquote(self.dirMaster_.base_dir), build_sub_dir = Utils.shellquote(bPaths.build_sub_dir), local_dir=Utils.shellquote(bPaths.local_dir), num_cores=self.num_cores(), CC=self.CC, CXX=self.CXX)
        Utils.mkdir(os.path.dirname(bPaths.local_dir))
        if "" != cmd and self.args.verbose:
            print cmd
        if "git" == pack.libType_:
            Utils.mkdir(bPaths.build_dir)
            if fromGitTag:
                self.__buildFromGitTag(packVer, cmd)
            else:
                self.__buildFromGitBranch(packVer, cmd)
        elif "git-headeronly" == pack.libType_:
            if fromGitTag:
                self.__gitTag(packVer)
            else:
                self.__gitBranch(packVer)
        elif "file" == pack.libType_:
            Utils.mkdir(bPaths.build_dir)
            self.__buildFromFile(packVer, cmd)
        else:
            raise Exception("Unrecognized lib type " + str(pack.libType_))
        if Utils.isMac():
            libPath = os.path.join(bPaths.local_dir, "lib")
            if(os.path.exists(libPath)):
                Utils.fixDyLibOnMac(libPath)
        
    def __defaultBibBuild(self, package, version):
        if "develop" == version or "release" in version or "master" == version:
            self.__defaultBuild(package, version, False)
        else:
            self.__defaultBuild(package, version, True)
        
    def updateBibProjects(self, bibProjects):
        inLibs = bibProjects.split(",")
        for lib in inLibs:
            if ":" not in lib.lower():
                raise Exception("Need to give version for " + lib)
            else:
                libSplit = lib.split(":")
                #self.packages_.addPackage(self.setUpsNeeded,LibNameVer(libSplit[0].lower(),libSplit[1]))
                self.setUpsNeeded.append(LibNameVer(libSplit[0].lower(),libSplit[1]))
        for set in self.setUpsNeeded:
            self.packages_.checkForPackVer(set)
            pack = self.__package(set.name)
            bPaths = pack.versions_[set.version].bPaths_
            if os.path.exists(bPaths.local_dir):
                print "Removing " + CT.boldBlack(bPaths.local_dir)
                Utils.rm_rf(bPaths.local_dir)
        for set in self.setUpsNeeded:
            pack = self.__package(set.name)
            bPath = pack.versions_[set.version].bPaths_
            if os.path.exists(os.path.join(bPath.build_dir,set.name, "makefile-common.mk")):
                os.remove(os.path.join(bPath.build_dir,set.name, "makefile-common.mk"))
            self.__setup(set.name, set.version)
        for p in self.installed:
            print p.name + ":" + str(p.version), CT.boldGreen("installed")

        for p in self.failedInstall:
            print  p.name + ":" + str(p.version), CT.boldRed("failed to install")
        
    
    def installRPackageSource(self,version, sourceFile):
        rPack = self.__package("r")
        if not rPack.hasVersion(version):
            raise Exception("No set up for version " + str(version) + " for " + str("R"))
        bPath = rPack.versions_[version].bPaths_
        for pack in sourceFile.split(","):
            rHomeLoc = "bin/R RHOME"
            if Utils.isMac():
                rHomeLoc = "R.framework/Resources/bin/R RHOME"
            cmd = """echo 'install.packages(\"{SOURCEFILE}\", repos = NULL, type="source", Ncpus = {num_cores}, lib =.libPaths()[length(.libPaths()  )])' | $({local_dir}/{RHOMELOC})/bin/R --slave --vanilla
                """.format(local_dir=Utils.shellquote(bPath.local_dir).replace(' ', '\ '),SOURCEFILE = pack, RHOMELOC =rHomeLoc, num_cores=self.num_cores())
            print CT.boldBlack(cmd)
            cmd = " ".join(cmd.split())
            Utils.run(cmd)

    def installRPackageName(self,version, packageName):
        rPack = self.__package("r")
        if not rPack.hasVersion(version):
            raise Exception("No set up for version " + str(version) + " for " + str("R"))
        bPath = rPack.versions_[version].bPaths_
        for pack in packageName.split(","):
            rHomeLoc = "bin/R RHOME"
            if Utils.isMac():
                rHomeLoc = "R.framework/Resources/bin/R RHOME"
            cmd = """echo 'install.packages(\"{PACKAGENAME}\", repos=\"http://cran.us.r-project.org\", Ncpus = {num_cores}, lib =.libPaths()[length(.libPaths()  )])'  | $({local_dir}/{RHOMELOC})/bin/R --slave --vanilla
                """.format(local_dir=Utils.shellquote(bPath.local_dir).replace(' ', '\ '),PACKAGENAME = pack, RHOMELOC =rHomeLoc,num_cores=self.num_cores() )
            print CT.boldBlack(cmd)
            cmd = " ".join(cmd.split())
            Utils.run(cmd)

    def boost(self, version):
        self.__defaultBuild("boost", version)

    def r(self, version):
        self.__defaultBuild("r", version)

    def bamtools(self, version):
        self.__defaultBuild("bamtools", version)

    def bibcpp(self, version):
        self.__defaultBibBuild("bibcpp", version)

    def bibseq(self, version):
        self.__defaultBibBuild("bibseq", version)
        
    def twobit(self, version):
        self.__defaultBibBuild("twobit", version)
            
    def sharedMutex(self, version):
        self.__defaultBibBuild("sharedmutex", version)
    
    def bibseqDev(self, version):
        self.__defaultBibBuild("bibseqdev", version)
        
    def SeekDeep(self, version):
        self.__defaultBibBuild("seekdeep", version)
    
    def SeekDeepDev(self, version):
        self.__defaultBibBuild("seekdeepdev", version)
        
    def seqserver(self, version):
        self.__defaultBibBuild("seqserver", version)
        
    def njhRInside(self, version):
        self.__defaultBibBuild("njhrinside", version)
        
    def cppprogutils(self, version):
        self.__defaultBibBuild("cppprogutils", version)
    
    def jsoncpp(self, version):
        self.__defaultBuild("jsoncpp", version)
        
    def mongoc(self, version):
        self.__defaultBuild("mongoc", version)
        
    def mongocxx(self, version):
        package = "mongocxx"
        pack = self.__package(package)
        if not pack.hasVersion(version):
            raise Exception("No set up for version " + str(version) + " for " + str(package))
        packVer = pack.versions_[version]
        bPaths = packVer.bPaths_
        pack.defaultBuildCmd_ = pack.defaultBuildCmd_.format(mongoc_ver = packVer.depends_[0].version,external = self.dirMaster_.base_dir, build_sub_dir = Utils.shellquote(bPaths.build_sub_dir), local_dir=Utils.shellquote(bPaths.local_dir), num_cores=self.num_cores(), CC=self.CC, CXX=self.CXX)
        self.__defaultBuild("mongocxx", version)
    
    def cppcms(self, version):
        self.__defaultBuild("cppcms", version)

    def armadillo(self, version):
        self.__defaultBuild("armadillo", version)

    def zi_lib(self, version):
        self.__defaultBuild("zi_lib", version)
        
    def pstreams(self, version):
        self.__defaultBuild("pstreams", version)

    def cppitertools(self, version):
        self.__defaultBuild("cppitertools", version)
    
    def dlib(self, version):
        self.__defaultBuild("dlib", version)
        
    def libsvm(self, version):
        self.__defaultBuild("libsvm", version)

    def catch(self, version):
        self.__defaultBuild("catch", version)
        
    def mathgl(self, version):
        self.__defaultBuild("mathgl", version)
        
    def magic(self, version):
        self.__defaultBuild("magic", version)
        
    def downloadFiles(self):
        for set in self.setUpsNeeded:
            topTempDir = os.path.join(self.dirMaster_.base_dir, "temp")
            self.packages_.checkForPackVer(set)
            pack = self.__package(set.name) 
            packVer = pack.versions_[set.version]
            downloadDir = os.path.join(self.dirMaster_.ext_tars, pack.name_)
            Utils.mkdir(downloadDir)
            if pack.bibProject_:
                downloadCmd = "python ./configure.py -CC {CC} -CXX {CXX} -externalLibDir {external} && ./setup.py --compfile compfile.mk --justDownload".format(external = Utils.shellquote(self.dirMaster_.base_dir), num_cores=self.num_cores(), CC=self.CC, CXX=self.CXX)
                Utils.mkdir(topTempDir)
                packVer = pack.versions_[set.version]
                tempDir = os.path.join(topTempDir, pack.name_)
                cloneCmd = "git clone {url} {d}".format(url=packVer.bPaths_.url, d = tempDir)
                tagCmd = "git checkout {tag}".format(tag=packVer.nameVer_.version.replace("__", "/"))
                Utils.run(cloneCmd)
                Utils.run_in_dir(tagCmd, tempDir)
                Utils.run_in_dir(downloadCmd, tempDir)
                if "develop" == set.version or "master" == set.version or "release" in set.version:
                    archiveCmd = "git archive --prefix={name}/ -o {downloadDir}/{version}.tar.gz HEAD".format(name = pack.name_, downloadDir = downloadDir, version = set.version)
                    Utils.run_in_dir(archiveCmd, tempDir)
                shutil.rmtree(tempDir)
            if pack.bibProject_ and ("develop" == set.version or "master" == set.version or "release" in set.version):
                pass
            else:
                url = packVer.getDownloadUrl()
                dest = os.path.join(self.dirMaster_.ext_tars, packVer.nameVer_.name)
                print ("Downloading " + CT.boldGreen(url) + " to " + CT.boldBlue(dest))
                if pack.libType_.startswith("git"):
                    fnp = Utils.get_file(url, dest)
                else:
                    fnp = Utils.get_file_if_size_diff(url, dest)
                
        if os.path.exists(os.path.join(self.dirMaster_.base_dir, "temp")) and os.listdir(os.path.join(self.dirMaster_.base_dir, "temp")) == []:
            shutil.rmtree(os.path.join(self.dirMaster_.base_dir, "temp"))
        print ("Now run \"./setup.py --compfile compfile.mk --outMakefile makefile-common.mk --noInternet\" to build libraries")

    def externalChecks(self):
        ccWhich = Utils.which(self.CC)
        cxxWhich = Utils.which(self.CXX)
        cmakeWhich = Utils.which("cmake")
        gitWhich = Utils.which("git")
        if not ccWhich or not cxxWhich or not cmakeWhich or not gitWhich:
            if not ccWhich:
                print CT.boldRed("Could not find c compiler " + CT.purple + self.CC)
                if self.args.compfile:
                    print "Change CC in " + self.args.compfile
                else:
                    print "Can supply another c compiler by using -CC [option] or by defining bash environmental CC "
                print ""
            if not cxxWhich:
                print CT.boldRed("Could not find c++ compiler " + CT.purple + self.CXX)
                if self.args.compfile:
                    print "Change CXX in " + self.args.compfile
                else:
                    print "Can supply another c++ compiler by using -CXX [option] or by defining bash environmental CXX "
                print ""
            if not cmakeWhich:
                print CT.boldRed("Could not find " + CT.purple + "cmake")
                if Utils.isMac():
                    print "If you have brew, you can install via, brew update && brew install cmake, otherwise you can follow instructions from http://www.cmake.org/install/"
                else:
                    print "On ubuntu to install latest cmake do the following"
                    print "sudo add-apt-repository ppa:george-edison55/cmake-3.x"
                    print "sudo apt-get update"
                    print "sudo apt-get install cmake"
            if not gitWhich:
                print "Can't find git"
            raise Exception("")
    def clearCache(self):
        Utils.rm_rf(self.dirMaster_.cache_dir)
        Utils.mkdir(self.dirMaster_.cache_dir)

def ubuntu(self):
        pkgs = """libbz2-dev python2.7-dev cmake libpcre3-dev zlib1g-dev libgcrypt11-dev libicu-dev
python doxygen doxygen-gui auctex xindy graphviz libcurl4-openssl-dev""".split()



def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--compfile', type=str, nargs=1)
    parser.add_argument('--libs', type=str, help="The libraries to install")
    parser.add_argument('--printLibs', action = "store_true", help="Print Available Libs")
    parser.add_argument('--printGitRefs', action = "store_true", help="Print Git branhes and tags for git projects")
    parser.add_argument('--forceUpdate', action = "store_true", help="Remove already installed libs and re-install")
    parser.add_argument('--updateBibProjects', type = str, help="Remove already installed libs and re-install")
    parser.add_argument('--CC', type=str, nargs=1)
    parser.add_argument('--CXX', type=str, nargs=1)
    parser.add_argument('--instRPackageName',type=str, nargs=1)
    parser.add_argument('--instRPackageSource',type=str, nargs=1) 
    parser.add_argument('--addBashCompletion', dest = 'addBashCompletion', action = 'store_true')
    parser.add_argument('--numCores', type=str)
    parser.add_argument('--outMakefile', type=str)
    parser.add_argument('--overWrite', action = 'store_true')
    parser.add_argument('--append', action = 'store_true')
    parser.add_argument('--noInternet', action = 'store_true')
    parser.add_argument('--justDownload', action = 'store_true')
    parser.add_argument('--verbose', action = 'store_true')
    parser.add_argument('--clearCache', action = 'store_true')
    return parser.parse_args()



def main():
    args = parse_args()
    s = Setup(args)
    s.externalChecks()
    if(args.instRPackageName):
        s.installRPackageName(args.instRPackageName[0], s.packages_["r"].defaultVersion_)
        return 0
    if(args.instRPackageSource):
        s.installRPackageSource(args.instRPackageSource[0], s.packages_["r"].defaultVersion_)
        return 0
    if args.updateBibProjects:
        s.updateBibProjects(args.updateBibProjects)
        return 0
    if args.printLibs:
        s.printAvailableSetUps()
        return 0
    elif args.addBashCompletion:
        if(os.path.isdir("./bashCompletes")):
            cmd = "echo >> ~/.bash_completion && cat bashCompletes/* >> ~/.bash_completion"
            Utils.run(cmd)
        if(os.path.isdir("./bash_completion.d")):
            cmd = "echo >> ~/.bash_completion && cat bash_completion.d/* >> ~/.bash_completion"
            Utils.run(cmd)
        if(os.path.isdir("./etc/bash_completion.d")):
            cmd = "echo >> ~/.bash_completion && cat ./etc/bash_completion.d/* >> ~/.bash_completion"
            Utils.run(cmd)
    else:
        if len(s.setUpsNeeded) == 0 and not args.compfile:
            s.printAvailableSetUps()
            return 1
        elif args.printGitRefs:
            s.printGitRefs()
            return 0
        else:
            if args.justDownload:
                s.downloadFiles()
            else:
                s.setup()
                if args.outMakefile:
                    packVers = []
                    for set in s.setUpsNeeded:
                        s.packages_.addPackage(packVers,set)
                    s.packages_.writeMakefile(packVers, args.outMakefile, args.overWrite, args.append)
                return 0

if __name__ == '__main__':
    main()
    
    
    
