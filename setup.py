#!/usr/bin/env python



import subprocess, sys, os, argparse
from collections import namedtuple
import shutil
from _curses import version
sys.path.append("scripts/pyUtils")
sys.path.append("scripts/setUpScripts")
from utils import Utils
from genFuncs import genHelper 
from color_text import ColorText as CT


BuildPaths = namedtuple("BuildPaths", 'url build_dir build_sub_dir local_dir')

class LibDirMaster():
    def __init__(self,externalLoc):
        self.base_dir = externalLoc; #top dir to hold tars,build, local directories
        
        self.ext_tars = os.path.join(self.base_dir, "tarballs") #location to keep tarballs of programs/libraries downloads
        self.ext_build = os.path.join(self.base_dir, "build") #location for the building of programs/libraries
        self.install_dir = os.path.join(self.base_dir, "local") #location for the final install of programs/libraries
        
        Utils.mkdir(self.ext_tars) #tar storage directory
        Utils.mkdir(self.ext_build) #build directory
        Utils.mkdir(self.install_dir) #local directory

def shellquote(s):
    # from http://stackoverflow.com/a/35857
    return "'" + s.replace("'", "'\\''") + "'"

class CPPLibPackage():
    def __init__(self, name, defaultBuildCmd, dirMaster, libType):
        self.name_ = name
        self.defaultBuildCmd_ = defaultBuildCmd
        self.version_ = {}
        self.externalLibDir_ = dirMaster
        if "git" != libType or "file" != libType:
            raise Exception("libType should be 'git' or 'file', not " + str(libType))
        self.libType_ = libType #should be git or file
    
    def addVersion(self, url, verName):
        build_dir = os.path.join(self.externalLibDir_.ext_build, self.name_, self.verName)
        build_sub_dir = os.path.join(self.externalLibDir_.ext_build, self.name_, self.verName, self.name_)
        local_dir = os.path.join(self.externalLibDir_.install_dir, self.name_, verName, self.name_)
        self.version_[verName] = BuildPaths(url, build_dir, build_sub_dir, local_dir)
    
    def addHeaderOnlyVersion(self, url, verName):
        '''set up for header only libraries, these just need
         the header copied no need for build_dir build_sub_dir '''
        local_dir = os.path.join(self.externalLibDir_.install_dir, self.name_, verName, self.name_)
        self.version_[verName] = BuildPaths(url, "", "", local_dir)
        


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
        '''
        self.packages_["mlpack"] = self.__mlpack()
        self.packages_["liblinear"] = self.__liblinear()
        self.packages_["mathgl"] = self.__mathgl()
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
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git")
        pack.addHeaderOnlyVersion(url, "master")
        return pack
    
    def __pstreams(self):
        name = "pstreams"
        url = 'https://github.com/nickjhathaway/pstreams'
        buildCmd = ""
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git")
        pack.addHeaderOnlyVersion(url, "master")
        pack.addHeaderOnlyVersion(url, "RELEASE_0_8_1")
        return pack

    def __bamtools(self):
        url = 'https://github.com/pezmaster31/bamtools.git'
        name = "bamtools"
        buildCmd = "mkdir -p build && cd build && CC={CC} CXX={CXX} cmake -DCMAKE_INSTALL_PREFIX:PATH={local_dir} .. && make -j {num_cores} install"
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git")
        pack.addVersion(url, "2.4.0")
        pack.addVersion(url, "2.3.0")
        return pack
    
    def __jsoncpp(self):
        url = "https://github.com/open-source-parsers/jsoncpp.git"
        name = "jsoncpp"
        buildCmd = "mkdir -p build && cd build && CC={CC} CXX={CXX} cmake -DCMAKE_CXX_FLAGS=-fPIC -DCMAKE_EXE_LINKER_FLAGS=-fPIC -DCMAKE_INSTALL_PREFIX:PATH={local_dir} ..  && make -j {num_cores} install"
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git")
        pack.addVersion(url, "1.6.5")
        pack.addVersion(url, "master")
        return pack
    
    def __mongoc(self):
        url = "https://github.com/mongodb/mongo-c-driver"
        name = "mongoc"
        if Utils.isMac():
            buildCmd = "cd build && CC={CC} CXX={CXX} PKG_CONFIG_PATH=/usr/local/opt/openssl/lib/pkgconfig:{ext_dir}/local/mongoc/lib/pkgconfig:$PKG_CONFIG_PATH cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX={local_dir} .. && make -j {num_cores} && make install"
        else:
            buildCmd = "cd build && CC={CC} CXX={CXX} PKG_CONFIG_PATH={ext_dir}/local/mongoc/lib/pkgconfig:$PKG_CONFIG_PATH cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX={local_dir} .. && make -j {num_cores} && make install"
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git")
        pack.addVersion(url, "1.3.3")
        return pack
    
    def __mongocxx(self):
        url = "https://github.com/mongodb/mongo-cxx-driver"
        name = "mongocxx"
        if Utils.isMac():
            buildCmd = "cd build && CC={CC} CXX={CXX} PKG_CONFIG_PATH=/usr/local/opt/openssl/lib/pkgconfig:{ext_dir}/local/mongoc/lib/pkgconfig:$PKG_CONFIG_PATH cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX={local_dir} .. && make -j {num_cores} && make install"
        else:
            buildCmd = "cd build && CC={CC} CXX={CXX} PKG_CONFIG_PATH={ext_dir}/local/mongoc/lib/pkgconfig:$PKG_CONFIG_PATH cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX={local_dir} .. && make -j {num_cores} && make install"
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git")
        pack.addVersion(url, "3.0.1")
        return self.__package_dirs(url, name)

    def __cppitertools(self):
        url = 'https://github.com/ryanhaining/cppitertools.git'
        name = "cppitertools"
        buildCmd = ""
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git")
        pack.addHeaderOnlyVersion(url, "master")
        pack.addHeaderOnlyVersion(url, "v0.1")
        return pack

    def __catch(self):
        url = 'https://github.com/philsquared/Catch.git'
        name = "catch"
        buildCmd = ""
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git")
        pack.addHeaderOnlyVersion(url, "v1.3.3")
        return pack

    def __r(self):
        name = "R"
        rHomeLoc = "bin/R RHOME"
        if Utils.isMac():
            rHomeLoc = "R.framework/Resources/bin/R RHOME"
        #'install.packages(c(\"gridExtra\", \"ape\", \"ggplot2\", \"seqinr\",\"Rcpp\", \"RInside\", \"devtools\"),
        buildCmd = """./configure --prefix={local_dir} --enable-R-shlib --with-x=no CC={CC} CXX={CXX} OBJC={CC}
                && make -j {num_cores}
                && make install
                && echo 'install.packages(c(\"gridExtra\", \"ape\", \"ggplot2\", \"seqinr\",\"Rcpp\", \"RInside\"),
                repos=\"http://cran.us.r-project.org\", Ncpus = {num_cores}, lib =.libPaths()[length(.libPaths()  )])' | $({local_dir}/{RHOMELOC})/bin/R --slave --vanilla
                """.format(RHOMELOC = rHomeLoc)
        buildCmd = " ".join(buildCmd.split())
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "file")
        pack.addVersion("http://baileylab.umassmed.edu/sourceCodes/R/R-3.2.2.tar.gz", "3.2.2")
        pack.addVersion("http://baileylab.umassmed.edu/sourceCodes/R/R-3.2.1.tar.gz", "3.2.1")
        pack.addVersion("http://baileylab.umassmed.edu/sourceCodes/R/R-3.2.0.tar.gz", "3.2.0")
        pack.addVersion("http://baileylab.umassmed.edu/sourceCodes/R/R-3.1.3.tar.gz", "3.1.3")
        return pack

    def __armadillo(self):
        name = "armadillo"
        buildCmd = "mkdir -p build && cd build && CC={CC} CXX={CXX} cmake -DCMAKE_INSTALL_PREFIX:PATH={local_dir} .. && make -j {num_cores} install"
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "file")
        pack.addVersion("http://baileylab.umassmed.edu/sourceCodes/armadillo/armadillo-6.200.3.tar.gz", "6.200.3")
        pack.addVersion("http://baileylab.umassmed.edu/sourceCodes/armadillo/armadillo-6.100.0.tar.gz", "6.100.0")
        pack.addVersion("http://baileylab.umassmed.edu/sourceCodes/armadillo/armadillo-5.600.2.tar.gz", "5.600.2")
        return pack
    '''
    def __mlpack(self):
        url = "http://www.mlpack.org/files/mlpack-1.0.8.tar.gz"
        armadillo_dir = shellquote(i.local_dir).replace("mlpack", "armadillo")
        boost_dir = shellquote(i.local_dir).replace("mlpack", "boost")
        cmd = """
        mkdir -p build
        && cd build
        && CC={CC} CXX={CXX} cmake -D DEBUG=OFF -D PROFILE=OFF
         -D ARMADILLO_LIBRARY={armadillo_dir}/lib/libarmadillo.so.4.0.2
         -D ARMADILLO_INCLUDE_DIR={armadillo_dir}/include/
         -D CMAKE_INSTALL_PREFIX:PATH={local_dir} ..
         -DBoost_NO_SYSTEM_PATHS=TRUE -DBOOST_INCLUDEDIR={boost}/include/ -DBOOST_LIBRARYDIR={boost}/lib/
        && make -j {num_cores} install
        """.format(local_dir=shellquote(i.local_dir),
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
            """.format(local_dir=shellquote(i.local_dir))
        cmd = " ".join(cmd.split())
        return self.__package_dirs(url, "liblinear")

    def __mathgl(self):
        #url = "http://freefr.dl.sourceforge.net/project/mathgl/mathgl/mathgl%202.2.1/mathgl-2.2.1.tar.gz"
        url = "http://baileylab.umassmed.edu/sourceCodes/mathgl/mathgl-2.2.1.tar.gz"
        if (self.args.clang):
            cmd = """mkdir -p build && cd build && CC={CC} CXX={CXX} cmake -DCMAKE_INSTALL_PREFIX:PATH={local_dir} -Denable-pthread=ON -Denable-openmp=OFF .. 
            && make -j {num_cores} install""".format(
            local_dir=shellquote(i.local_dir), num_cores=self.num_cores(), CC=self.CC, CXX=self.CXX)
        else:
            cmd = """mkdir -p build && cd build && CC={CC} CXX={CXX} cmake -DCMAKE_INSTALL_PREFIX:PATH={local_dir}  .. 
            && make -j {num_cores} install""".format(
            local_dir=shellquote(i.local_dir), num_cores=self.num_cores(), CC=self.CC, CXX=self.CXX)
        cmd = " ".join(cmd.split())
        return self.__package_dirs(url, "mathgl")
    '''
    
    def __cppcms(self):
        name = "cppcms"
        buildCmd = "mkdir -p build && cd build && CC={CC} CXX={CXX} cmake -DCMAKE_INSTALL_PREFIX:PATH={local_dir} .. && make -j {num_cores} install"
        if(sys.platform == "darwin"):
            buildCmd += " && install_name_tool -change libbooster.0.dylib {local_dir}/lib/libbooster.0.dylib {local_dir}/lib/libcppcms.1.dylib"
        buildCmd = " ".join(buildCmd.split())
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "file")
        pack.addVersion("http://baileylab.umassmed.edu/sourceCodes/cppcms/cppcms-1.0.5.tar.bz2", "1.0.5")
        return pack

    def __dlib(self):
        name = "dlib"
        buildCmd = "mkdir {local_dir} && cp -a * {local_dir}/"
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "file")
        pack.addVersion("http://freefr.dl.sourceforge.net/project/dclib/dlib/v18.7/dlib-18.7.tar.bz2", "18.7")
        return pack
    
    def __libsvm(self):
        name = "libsvm"
        buildCmd = "make && make lib && mkdir -p {local_dir} && cp -a * {local_dir}"
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "file")
        pack.addVersion("http://www.csie.ntu.edu.tw/~cjlin/libsvm/oldfiles/libsvm-3.18.tar.gz", "3.18")
        return pack
    
    def __cppprogutils(self):
        url = 'https://github.com/bailey-lab/cppprogutils.git'
        name = "cppprogutils"
        buildCmd = ""
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git")
        pack.addHeaderOnlyVersion(url, "develop")
        pack.addHeaderOnlyVersion(url, "1.0")
        return pack
    
    def __bibseq(self):
        url = "https://github.com/bailey-lab/bibseq.git"
        name = "bibseq"
        buildCmd = self.__bibProjectBuildCmd()
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git")
        pack.addVersion(url, "develop")
        pack.addVersion(url, "2.2.1")
        return pack
    
    def __bibseqDev(self):
        url = "https://github.com/bailey-lab/bibseqPrivate.git"
        name = "bibseqDev"
        buildCmd = self.__bibProjectBuildCmd()
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git")
        pack.addVersion(url, "master")
        return pack
    
    def __twobit(self):
        url = "https://github.com/weng-lab/TwoBit.git"
        name = "TwoBit"
        buildCmd = self.__bibProjectBuildCmd()
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git")
        pack.addVersion(url, "develop")
        pack.addVersion(url, "1.0")
        return pack
    
    def __sharedMutex(self):
        url = "https://github.com/nickjhathaway/cpp_shared_mutex.git"
        name = "sharedMutex"
        buildCmd = self.__bibProjectBuildCmd()
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git")
        pack.addVersion(url, "develop")
        pack.addVersion(url, "v0.1")
        return pack 
      
    def __SeekDeep(self):
        url = "https://github.com/bailey-lab/SeekDeep.git"
        name = "SeekDeep"
        buildCmd = self.__bibProjectBuildCmd()
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git")
        pack.addVersion(url, "develop")
        pack.addVersion(url, "2.2.1")
        return pack
    
    def __SeekDeepDev(self):
        url = "https://github.com/bailey-lab/SeekDeepPrivate.git"
        name = "SeekDeepDev"
        buildCmd = self.__bibProjectBuildCmd()
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git")
        pack.addVersion(url, "master")
        return pack
    
    def __seqserver(self):
        url = "https://github.com/nickjhathaway/seqServer.git"
        name = "seqServer"
        buildCmd = self.__bibProjectBuildCmd()
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git")
        pack.addVersion(url, "develop")
        pack.addVersion(url, "1.2.1")
        return pack
    
    def __njhRInside(self):
        url = "https://github.com/nickjhathaway/njhRInside.git"
        name = "njhRInside"
        buildCmd = self.__bibProjectBuildCmd()
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git")
        pack.addVersion(url, "develop")
        pack.addVersion(url, "1.1.1")
        return pack
    
    def __bibcpp(self):
        url = "https://github.com/umass-bib/bibcpp.git"
        name = "bibcpp"
        buildCmd = self.__bibProjectBuildCmd()
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "git")
        pack.addVersion(url, "develop")
        pack.addVersion(url, "1.2.1")
        return pack

    def __boost(self):
        name = "boost"
        buildCmd = ""
        boostLibs = "filesystem,iostreams,system"
        if Utils.isMac():
            #print "here"
            setUpDir = os.path.dirname(os.path.abspath(__file__))
            gccJamLoc =  os.path.join(setUpDir, "scripts/etc/boost/gcc.jam")
            gccJamOutLoc = "{build_dir}/tools/build/src/tools/gcc.jam"
            #print gccJamLoc
            #print gccJamOutLoc
            installNameToolCmd  = """ 
            && install_name_tool -change $(otool -L {local_dir}/lib/libboost_filesystem.dylib | egrep -o "\\S.*libboost_system.dylib") {local_dir}/lib/libboost_system.dylib {local_dir}/lib/libboost_filesystem.dylib
            && install_name_tool -id {local_dir}/lib/libboost_filesystem.dylib {local_dir}/lib/libboost_filesystem.dylib
            && install_name_tool -id {local_dir}/lib/libboost_iostreams.dylib {local_dir}/lib/libboost_iostreams.dylib
            && install_name_tool -id {local_dir}/lib/libboost_system.dylib {local_dir}/lib/libboost_system.dylib
            """
        if self.args.clang:
            if Utils.isMac():
                buildCmd = """./bootstrap.sh --with-toolset=clang --prefix={local_dir} --with-libraries=""" + boostLibs + """
                  &&  ./b2  toolset=clang cxxflags=\"-stdlib=libc++ -std=c++14\" linkflags=\"-stdlib=libc++\" -j {num_cores} install 
                  &&  install_name_tool -change libboost_system.dylib {local_dir}/lib/libboost_system.dylib {local_dir}/lib/libboost_filesystem.dylib
                  """
            else:
                buildCmd = """./bootstrap.sh --with-toolset=clang --prefix={local_dir}  --with-libraries=""" + boostLibs + """ &&  ./b2 toolset=clang cxxflags=\"-std=c++14\" -j {num_cores} install"""
        elif "g++" in self.args.CXX:
            if "-" in self.args.CXX:
                gccVer = self.args.CXX[(self.CXX.find("-") + 1):]
                if Utils.isMac():
                    buildCmd = "cp " + gccJamLoc + "  " + gccJamOutLoc + """ && echo "using gcc : """ + str(gccVer) + """ : {CXX} : <linker-type>darwin ;" >> project-config.jam 
                     && ./bootstrap.sh --with-toolset=gcc --prefix={local_dir} --with-libraries=""" + boostLibs + """
                     && ./b2 --toolset=gcc-4.8 -j {num_cores} install 
                     """ + installNameToolCmd
                else:
                    buildCmd = """echo "using gcc : """ + str(gccVer) + """ : {CXX};" >> project-config.jam && ./bootstrap.sh --with-toolset=gcc --prefix={local_dir} --with-libraries=""" + boostLibs + """
                     && ./b2 --toolset=gcc-4.8 -j {num_cores} install 
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
        cmd = " ".join(cmd.split())
        pack = CPPLibPackage(name, buildCmd, self.dirMaster_, "file")
        pack.addVersion("http://baileylab.umassmed.edu/sourceCodes/boost/boost_1_58_0.tar.bz2", "1_58_0")
        pack.addVersion("http://baileylab.umassmed.edu/sourceCodes/boost/boost_1_59_0.tar.bz2", "1_59_0")
        pack.addVersion("http://baileylab.umassmed.edu/sourceCodes/boost/boost_1_60_0.tar.bz2", "1_60_0")
        return pack

    def __bibProjectBuildCmd(self):
        cmd = """
        python ./configure.py -CC {CC} -CXX {CXX} -externalLibDir {external} -prefix {localTop} 
        && python ./setup.py --compfile compfile.mk --numCores {num_cores}
        && make -j {num_cores} && make install"""
        cmd = " ".join(cmd.split())
        return cmd
    
class Setup:
    def __init__(self, args):
        self.extDirLoc = "" # the location where the libraries will be installed
        #if no compile file set up and assume external is next to setup.py
        if not args.compfile:
            self.extDirLoc = os.path.abspath(os.path.join(os.path.dirname(__file__), "external"))
        else:
            self.extDirLoc = os.path.abspath(self.parseForExtPath(args.compfile[0]))
        self.dirMaster_ = LibDirMaster(self.extDirLoc)
        self.args = args # command line arguments parsed by argument parser
        self.setUps = {} # all available set ups
        self.setUpsNeeded = {} # the setups that need to be done
        self.installed = [] # the setups that able to install
        self.failedInstall = [] # the setups that failed
        self.CC = "" # the c compilier being used
        self.CXX = "" # the c++ compilier being used
        self.__initSetUpFuncs()
        self.__processArgs()
        self.packages_ = Paths(self.extDirLoc, self.args) # path object to hold the paths for install
        
    def setup(self):
        if self.args.forceUpdate:
            for set in self.setUpsNeeded.keys():
                if not set in self.setUps.keys():
                    print CT.boldBlack( "Unrecognized option ") + CT.boldRed(set)
                else:
                    self.rmDirsForLib(set)
                        
        for set in self.setUpsNeeded.keys():
            if not set in self.setUps.keys():
                print CT.boldBlack( "Unrecognized option ") + CT.boldRed(set)
            else:
                self.__setup(set, self.setUps[set])

        for p in self.installed:
            print p, CT.boldGreen("installed")

        for p in self.failedInstall:
            print  p, CT.boldRed("failed to install")

    def __initSetUpFuncs(self):
        self.setUps = {"zi_lib": self.zi_lib,
                       "boost": self.boost,
                       "cppitertools": self.cppitertools,
                       "catch": self.catch,
                       "cppprogutils": self.cppprogutils,
                       "r": self.r,
                       "bamtools": self.bamtools,
                       "cppcms": self.cppcms,
                       "mathgl": self.mathgl,
                       "armadillo": self.armadillo,
                       "mlpack": self.mlpack,
                       "liblinear": self.liblinear,
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
                       "sharedmutex" : self.sharedMutex
                       }
    def printAvailableSetUps(self):
        self.__initSetUpFuncs()
        print "Available installs:"
        print "To Install use ./setup.py --libs lib1,lib2,lib3"
        print "E.g. ./setup.py --libs bamtools,boost"
        installs = self.setUps.keys()
        installs.sort()
        for set in installs:
            print set

    def __processArgs(self):
        if self.args.libs:
            inLibs = self.args.libs.split(",")
            for lib in inLibs:
                if ":" not in lib.lower():
                    self.setUpsNeeded[lib.lower()] = ""
                else:
                    libSplit = lib.split(":")
                    self.setUpsNeeded[libSplit[0].lower()] = libSplit[1]
        if self.args.compfile:
            self.parseSetUpNeeded(self.args.compfile[0])
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
                if "#" in v:
                    valSplit = v.split("#")
                    if valSplit[0] == '1':
                        self.setUpsNeeded[k[4:].lower()] = valSplit[1]
                elif '1' == v:
                    self.setUpsNeeded[k[4:].lower()] = ""

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
        if 'CXX' in args:
            self.CXX = args['CXX']
    
    def rmDirsForLibs(self,libs):
        for l in libs:
            self.rmDirsForLib(l)
    
    def rmDirsForLib(self,lib):
        if lib not in self.setUps:
            print CT.boldBlack( "Unrecognized lib: ") + CT.boldRed(lib)
        else:
            p = self.__path(lib)
            if p.build_dir:
                print "Removing " + CT.boldBlack(p.build_dir)
                Utils.rm_rf(p.build_dir)
            if p.local_dir:
                print "Removing " + CT.boldBlack(p.local_dir)
                Utils.rm_rf(p.local_dir)
    

    def __package(self, name):
        return self.packages_.package(name)

    def __setup(self, name, version):
        if os.path.exists(self.__package(name).local_dir):
            print name, CT.boldGreen("found at ") + CT.boldBlack(self.__package(name).local_dir)
        else:
            print name, CT.boldRed("NOT"), "found; building..."
            try:
                builder_f()
                self.installed.append(name)
            except Exception as inst:
                print type(inst)
                print inst 
                print "failed to install " + name
                self.failedInstall.append(name)

    def showDefaultExample(self):
        print """
Need to supply compfile to parse for needed libraries and compilers"
by giving -compfile"

example:

python ./setUpScripts/generateCompFile.py -outFilename compfile.mk \
-externalLoc external \
-CC gcc -CXX g++ \
-outname seqTools \
-installName bibseq \
-neededLibs zi_lib,cppitertools,cppprogutils,boost,R,bamtools,pear,curl

python ./setup.py --compfile compfile.mk

make COMPFILE=compfile.mk -j {num_cores}
"""



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

    def __buildFromFile(self, bPath, cmd):
        print "\t Getting file..."
        fnp = Utils.get_file_if_size_diff(ibPath.url, self.packages_.ext_tars)
        Utils.clear_dir(bPath.build_dir)
        Utils.untar(fnp, bPath.build_dir)
        try:
            Utils.run_in_dir(cmd, bPath.build_sub_dir)
        except:
            print "\t Failed to build, removing {d}".format(d = bPath.local_dir)
            Utils.rm_rf(bPath.local_dir)
            sys.exit(1)
                
    def __buildFromGitBranch(self, bPath, cmd, branchName):
        if os.path.exists(bPath.build_dir):
            print "pulling from {url}".format(url=bPath.url)
            pCmd = "git checkout " + branchName + " && git pull"
            try:
                Utils.run_in_dir(pCmd, bPath.build_dir)
            except:
                print "failed to pull from {url} with {cmd}".format(url=bPath.url, cmd = pCmd)
                sys.exit(1)
        else:
            print "cloning from {url}".format(url=bPath.url)
            cCmd = "git clone -b " + branchName + " {url} {d}".format(url=bPath.url, d=bPath.build_dir)
            try:
                print self.packages_.ext_build
                Utils.run_in_dir(cCmd, self.packages_.ext_build)
            except:
                print "failed to clone from {url}".format(url=bPath.url)
                sys.exit(1)
        try:
            Utils.run_in_dir(cmd, bPath.build_dir)
        except:
            print("Failed to build, removing {d}".format(d = bPath.local_dir))
            Utils.rm_rf(bPath.local_dir)
            sys.exit(1)
    
    def __buildFromGitTag(self, bPath, cmd, tagName):
        if os.path.exists(bPath.build_dir):
            print "pulling from {url}".format(url=bPath.url)
            pCmd = "git checkout origin/master && git pull && git checkout " + tagName
            try:
                Utils.run_in_dir(pCmd, bPath.build_dir)
            except:
                print "failed to pull from {url}".format(url=bPath.url)
                sys.exit(1)
        else:
            print "cloning from {url}".format(url=bPath.url)
            cCmd = "git clone {url} {d}".format(url=bPath.url, d=bPath.build_dir)
            tagCmd = "git checkout {tag}".format(tag=tagName)
            try:
                print self.packages_.ext_build
                Utils.run_in_dir(cCmd, self.packages_.ext_build)
                Utils.run_in_dir(tagCmd, bPath.build_dir)
            except:
                print "failed to clone from {url}".format(url=bPath.url)
                sys.exit(1)
        try:
            Utils.run_in_dir(cmd, bPath.build_dir)
        except:
            Utils.rm_rf(bPath.local_dir)
            sys.exit(1)
    
    def __gitBranch(self, bPath, branchName):
        print "cloning from {url}".format(url=bPath.url)
        cCmd = "git clone -b {branch} {url} {d}".format(branch = branchName,url=bPath.url, d=bPath.build_dir)
        try:
            print self.packages_.ext_build
            Utils.run_in_dir(cCmd, self.packages_.ext_build)
        except:
            print "failed to clone branch {branch} from {url}".format(branch = branchName, url=bPath.url)
            sys.exit(1)
    
    def __gitTag(self, bPath, tagName):
        cmd = "git clone {url} {d}".format(url=bPath.url, d=shellquote(bPath.local_dir))
        tagCmd = "git checkout {tag}".format(tag=tagName)
        try:
            Utils.run(cmd)
            Utils.run_in_dir(tagCmd, bPath.local_dir)
        except:
            print "failed to clone from {url}".format(url=bPath.url)
            sys.exit(1)
        
    
    def installRPackageSource(self, sourceFile):
        i = self.__path("r")
        for pack in sourceFile.split(","):
            rHomeLoc = "bin/R RHOME"
            if Utils.isMac():
                rHomeLoc = "R.framework/Resources/bin/R RHOME"
            cmd = """echo 'install.packages(\"{SOURCEFILE}\", repos = NULL, type="source", Ncpus = {num_cores}, lib =.libPaths()[length(.libPaths()  )])' | $({local_dir}/{RHOMELOC})/bin/R --slave --vanilla
                """.format(local_dir=shellquote(i.local_dir).replace(' ', '\ '),SOURCEFILE = pack, RHOMELOC =rHomeLoc, num_cores=self.num_cores())
            print CT.boldBlack(cmd)
            cmd = " ".join(cmd.split())
            Utils.run(cmd)

    def installRPackageName(self, packageName):
        i = self.__path("r")
        for pack in packageName.split(","):
            rHomeLoc = "bin/R RHOME"
            if Utils.isMac():
                rHomeLoc = "R.framework/Resources/bin/R RHOME"
            cmd = """echo 'install.packages(\"{PACKAGENAME}\", repos=\"http://cran.us.r-project.org\", Ncpus = {num_cores}, lib =.libPaths()[length(.libPaths()  )])'  | $({local_dir}/{RHOMELOC})/bin/R --slave --vanilla
                """.format(local_dir=shellquote(i.local_dir).replace(' ', '\ '),PACKAGENAME = pack, RHOMELOC =rHomeLoc,num_cores=self.num_cores() )
            print CT.boldBlack(cmd)
            cmd = " ".join(cmd.split())
            Utils.run(cmd)

    def boost(self):
        #print "start"
        i = self.__path("boost")
        #boostLibs = "date_time,filesystem,iostreams,math,program_options,random,regex,serialization,signals,system,test,thread,log"
        boostLibs = "filesystem,iostreams,system"
        if Utils.isMac():
            #print "here"
            setUpDir = os.path.dirname(os.path.abspath(__file__))
            gccJamLoc =  os.path.join(setUpDir, "scripts/etc/boost/gcc.jam")
            gccJamOutLoc = os.path.abspath("{build_dir}/tools/build/src/tools/gcc.jam".format(build_dir = i.build_sub_dir))
            #print gccJamLoc
            #print gccJamOutLoc
            installNameToolCmd  = """ 
            && install_name_tool -change $(otool -L {local_dir}/lib/libboost_filesystem.dylib | egrep -o "\\S.*libboost_system.dylib") {local_dir}/lib/libboost_system.dylib {local_dir}/lib/libboost_filesystem.dylib
            && install_name_tool -id {local_dir}/lib/libboost_filesystem.dylib {local_dir}/lib/libboost_filesystem.dylib
            && install_name_tool -id {local_dir}/lib/libboost_iostreams.dylib {local_dir}/lib/libboost_iostreams.dylib
            && install_name_tool -id {local_dir}/lib/libboost_system.dylib {local_dir}/lib/libboost_system.dylib
            """.format(local_dir=i.local_dir)
        if self.args.clang:
             if Utils.isMac():
                cmd = """./bootstrap.sh --with-toolset=clang --prefix={local_dir} --with-libraries=""" + boostLibs + """
                  &&  ./b2  toolset=clang cxxflags=\"-stdlib=libc++ -std=c++14\" linkflags=\"-stdlib=libc++\" -j {num_cores} install 
                  &&  install_name_tool -change libboost_system.dylib {local_dir}/lib/libboost_system.dylib {local_dir}/lib/libboost_filesystem.dylib
                  """
                  #&&  install_name_tool -change libboost_system.dylib {local_dir}/lib/libboost_system.dylib {local_dir}/lib/libboost_thread.dylib
                #cmd = """wget https://github.com/boostorg/atomic/commit/6bb71fdd.diff && wget https://github.com/boostorg/atomic/commit/e4bde20f.diff&&  wget https://gist.githubusercontent.com/philacs/375303205d5f8918e700/raw/d6ded52c3a927b6558984d22efe0a5cf9e59cd8c/0005-Boost.S11n-include-missing-algorithm.patch&&  patch -p2 -i 6bb71fdd.diff&&  patch -p2 -i e4bde20f.diff&&  patch -p1 -i 0005-Boost.S11n-include-missing-algorithm.patch&&  echo "using clang;  " >> tools/build/v2/user-config.jam&&  ./bootstrap.sh --with-toolset=clang --prefix={local_dir} --with-libraries=""" + boostLibs + """  &&  ./b2  -d 2 toolset=clang cxxflags=\"-stdlib=libc++\" linkflags=\"-stdlib=libc++\" -j {num_cores} install &&  install_name_tool -change libboost_system.dylib {local_dir}/lib/libboost_system.dylib {local_dir}/lib/libboost_thread.dylib&&  install_name_tool -change libboost_system.dylib {local_dir}/lib/libboost_system.dylib {local_dir}/lib/libboost_filesystem.dylib""".format(local_dir=shellquote(i.local_dir).replace(' ', '\ '), num_cores=self.num_cores())
             else:
                cmd = """./bootstrap.sh --with-toolset=clang --prefix={local_dir}  --with-libraries=""" + boostLibs + """ &&  ./b2 toolset=clang cxxflags=\"-std=c++14\" -j {num_cores} install""".format(local_dir=shellquote(i.local_dir).replace(' ', '\ '), num_cores=self.num_cores())
                #cmd = """wget https://github.com/boostorg/atomic/commit/6bb71fdd.diff && wget https://github.com/boostorg/atomic/commit/e4bde20f.diff&&  wget https://gist.githubusercontent.com/philacs/375303205d5f8918e700/raw/d6ded52c3a927b6558984d22efe0a5cf9e59cd8c/0005-Boost.S11n-include-missing-algorithm.patch&&  patch -p2 -i 6bb71fdd.diff&&  patch -p2 -i e4bde20f.diff&&  patch -p1 -i 0005-Boost.S11n-include-missing-algorithm.patch&&  echo "using clang;  " >> tools/build/v2/user-config.jam&&  ./bootstrap.sh --with-toolset=clang --prefix={local_dir}  --with-libraries=""" + boostLibs + """ &&  ./b2  -d 2 toolset=clang -j {num_cores} install""".format(local_dir=shellquote(i.local_dir).replace(' ', '\ '), num_cores=self.num_cores())
        elif self.CXX == "g++-4.8":
            if Utils.isMac():
                cmd = "cp " + gccJamLoc + "  " + gccJamOutLoc + """ && echo "using gcc : 4.8 : g++-4.8 : <linker-type>darwin ;" >> project-config.jam && ./bootstrap.sh --with-toolset=gcc --prefix={local_dir} --with-libraries=""" + boostLibs + """
                 && ./b2 --toolset=gcc-4.8 -j {num_cores} install 
                 """ + installNameToolCmd
            else:
                cmd = """echo "using gcc : 4.8 : g++-4.8;" >> project-config.jam && ./bootstrap.sh --with-toolset=gcc --prefix={local_dir} --with-libraries=""" + boostLibs + """
                 && ./b2 --toolset=gcc-4.8 -j {num_cores} install 
                 """
        elif self.CXX == "g++-4.9":
            if Utils.isMac():
                cmd = "cp " + gccJamLoc + "  " + gccJamOutLoc + """ && echo "using gcc : 4.9 : g++-4.9 : <linker-type>darwin ;" >> project-config.jam && ./bootstrap.sh --with-toolset=gcc --prefix={local_dir} --with-libraries=""" + boostLibs + """
                 && ./b2 --toolset=gcc-4.9 -j {num_cores} install 
                 """ + installNameToolCmd
            else:
                cmd = """echo "using gcc : 4.9 : g++-4.9;" >> project-config.jam && CC={CC} CXX={CXX} ./bootstrap.sh --with-toolset=gcc --prefix={local_dir} --with-libraries=""" + boostLibs + """
                 && CC={CC} CXX={CXX}  ./b2 --toolset=gcc-4.9 -j {num_cores} install 
                 """
        elif self.CXX == "g++-5":
            if Utils.isMac():
                cmd = """echo "using gcc : 5 : g++-5;" >> project-config.jam && CC={CC} CXX={CXX} ./bootstrap.sh --with-toolset=gcc --prefix={local_dir} --with-libraries=""" + boostLibs + """
                 && CC={CC} CXX={CXX} ./b2 --toolset=gcc-5 -j {num_cores} install 
                 """ + installNameToolCmd
            else:
                cmd = """echo "using gcc : 5 : g++-5;" >> project-config.jam && CC={CC} CXX={CXX} ./bootstrap.sh --with-toolset=gcc --prefix={local_dir} --with-libraries=""" + boostLibs + """
                 && CC={CC} CXX={CXX}  ./b2 --toolset=gcc-5 -j {num_cores} install 
                 """
        elif self.CXX == "g++":
            if Utils.isMac():
                cmd = "cp " + gccJamLoc + "  " + gccJamOutLoc + """ && echo "using gcc : 4.9 : g++ : <linker-type>darwin ;" >> project-config.jam && ./bootstrap.sh --with-toolset=gcc --prefix={local_dir} --with-libraries=""" + boostLibs + """
                 && ./b2 --toolset=gcc-4.9 -j {num_cores} install 
                 """ + installNameToolCmd
            else:
                cmd = """echo "using gcc : 4.9 : g++;" >> project-config.jam && ./bootstrap.sh --with-toolset=gcc --prefix={local_dir} --with-libraries=""" + boostLibs + """
                 && ./b2 --toolset=gcc-4.9 -j {num_cores} install 
                 """
        cmd = " ".join(cmd.split())
        cmd = cmd.format(local_dir=shellquote(i.local_dir).replace(' ', '\ '), num_cores=self.num_cores(), CC=self.CC, CXX=self.CXX)
        print cmd
        self.__build(i, cmd)



    def r(self):
        i = self.__path("r")
        rHomeLoc = "bin/R RHOME"
        if Utils.isMac():
            rHomeLoc = "R.framework/Resources/bin/R RHOME"
        #'install.packages(c(\"gridExtra\", \"ape\", \"ggplot2\", \"seqinr\",\"Rcpp\", \"RInside\", \"devtools\"),
        cmd = """./configure --prefix={local_dir} --enable-R-shlib --with-x=no CC={CC} CXX={CXX} OBJC={CC}
                && make -j {num_cores}
                && make install
                && echo 'install.packages(c(\"gridExtra\", \"ape\", \"ggplot2\", \"seqinr\",\"Rcpp\", \"RInside\"),
                repos=\"http://cran.us.r-project.org\", Ncpus = {num_cores}, lib =.libPaths()[length(.libPaths()  )])' | $({local_dir}/{RHOMELOC})/bin/R --slave --vanilla
                """.format(local_dir=shellquote(i.local_dir).replace(' ', '\ '), num_cores=self.num_cores(), CC=self.CC, CXX=self.CXX, RHOMELOC = rHomeLoc)
        cmd = " ".join(cmd.split())
        self.__build(i, cmd)

    def bamtools(self):
        i = self.__path('bamtools')
        cmd = """git checkout v2.4.0 && mkdir -p build && cd build && CC={CC} CXX={CXX} cmake -DCMAKE_INSTALL_PREFIX:PATH={local_dir} .. 
        && make -j {num_cores} install""".format(
            local_dir=shellquote(i.local_dir), num_cores=self.num_cores(), CC=self.CC, CXX=self.CXX)
        cmd = " ".join(cmd.split())
        self.__buildFromGit(i, cmd)

    def bibcpp(self):
        i = self.__path('bibcpp')
        if "bibcpp" in self.setUpsNeeded and self.setUpsNeeded["bibcpp"] != "":
            self.__buildBibProjectBranch(i, self.setUpsNeeded["bibcpp"])
        else:    
            self.__buildBibProject(i)

    def bibseq(self):
        i = self.__path('bibseq')
        if "bibseq" in self.setUpsNeeded and self.setUpsNeeded["bibseq"] != "":
            self.__buildBibProjectBranch(i, self.setUpsNeeded["bibseq"])
        else:    
            self.__buildBibProject(i)
        
    def twobit(self):
        i = self.__path('twobit')
        if "twobit" in self.setUpsNeeded and self.setUpsNeeded["twobit"] != "":
            self.__buildBibProjectBranch(i, self.setUpsNeeded["twobit"])
        else:    
            self.__buildBibProject(i)
            
    def sharedMutex(self):
        i = self.__path('sharedmutex')
        if "sharedmutex" in self.setUpsNeeded and self.setUpsNeeded["sharedmutex"] != "":
            self.__buildBibProjectBranch(i, self.setUpsNeeded["sharedmutex"])
        else:    
            self.__buildBibProject(i)
    
        
    def bibseqDev(self):
        i = self.__path('bibseqdev')
        if "bibseqdev" in self.setUpsNeeded and self.setUpsNeeded["bibseqdev"] != "":
            self.__buildBibProjectBranch(i, self.setUpsNeeded["bibseqdev"])
        else:    
            self.__buildBibProject(i)
        
    def SeekDeep(self):
        i = self.__path('seekdeep')
        if "seekdeep" in self.setUpsNeeded and self.setUpsNeeded["seekdeep"] != "":
            self.__buildBibProjectBranch(i, self.setUpsNeeded["seekdeep"])
        else:    
            self.__buildBibProject(i)
    
    def SeekDeepDev(self):
        i = self.__path('seekdeepdev')
        if "seekdeepdev" in self.setUpsNeeded and self.setUpsNeeded["seekdeepdev"] != "":
            self.__buildBibProjectBranch(i, self.setUpsNeeded["seekdeepdev"])
        else:    
            self.__buildBibProject(i)
        
    def seqserver(self):
        i = self.__path('seqserver')
        if "seqserver" in self.setUpsNeeded and self.setUpsNeeded["seqserver"] != "":
            self.__buildBibProjectBranch(i, self.setUpsNeeded["seqserver"])
        else:    
            self.__buildBibProject(i)
        
    def njhRInside(self):
        i = self.__path('njhrinside')
        if "njhrinside" in self.setUpsNeeded and self.setUpsNeeded["njhrinside"] != "":
            self.__buildBibProjectBranch(i, self.setUpsNeeded["njhrinside"])
        else:    
            self.__buildBibProject(i)
        
    def cppprogutils(self):
        i = self.__path('cppprogutils')
        if "cppprogutils" in self.setUpsNeeded and self.setUpsNeeded["cppprogutils"] != "":
            self.__gitTag(i, self.setUpsNeeded["cppprogutils"])
        else:    
            self.__git(i)
    
    def jsoncpp(self):
        i = self.__path('jsoncpp')
        cmd = """mkdir -p build && cd build && CC={CC} CXX={CXX} cmake -DCMAKE_CXX_FLAGS=-fPIC -DCMAKE_EXE_LINKER_FLAGS=-fPIC -DCMAKE_INSTALL_PREFIX:PATH={local_dir} .. 
        && make -j {num_cores} install""".format(
            local_dir=shellquote(i.local_dir), num_cores=self.num_cores(),CC=self.CC, CXX=self.CXX)
        cmd = " ".join(cmd.split())
        self.__buildFromGit(i, cmd)
        
    def mongoc(self):
        i = self.__path('mongoc')
        if Utils.isMac():
            cmd = """sed -i.bak s/git:/http:/g .gitmodules && CC={CC} CXX={CXX}  PKG_CONFIG_PATH=/usr/local/opt/openssl/lib/pkgconfig:$PKG_CONFIG_PATH ./autogen.sh --prefix={local_dir}
            && make -j {num_cores}  && make install""".format(local_dir=shellquote(i.local_dir), num_cores=self.num_cores(),CC=self.CC, CXX=self.CXX)
        else:
            cmd = """sed -i.bak s/git:/http:/g .gitmodules && CC={CC} CXX={CXX} ./autogen.sh --prefix={local_dir}
            && make -j {num_cores}  && make install""".format(local_dir=shellquote(i.local_dir), num_cores=self.num_cores(),CC=self.CC, CXX=self.CXX)
        cmd = " ".join(cmd.split())
        branchName = "1.3.3"
        self.__buildFromGitTag(i, cmd, branchName)
        
    def mongocxx(self):
        i = self.__path('mongocxx')
        if Utils.isMac():
            cmd = """cd build && CC={CC} CXX={CXX} PKG_CONFIG_PATH=/usr/local/opt/openssl/lib/pkgconfig:{ext_dir}/local/mongoc/lib/pkgconfig:$PKG_CONFIG_PATH cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX={local_dir} .. 
            && make -j {num_cores} && make install""".format(local_dir=i.local_dir, num_cores=self.num_cores(),CC=self.CC, CXX=self.CXX, ext_dir=self.extDirLoc)
        else:
            cmd = """cd build && CC={CC} CXX={CXX} PKG_CONFIG_PATH={ext_dir}/local/mongoc/lib/pkgconfig:$PKG_CONFIG_PATH cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX={local_dir} .. 
            && make -j {num_cores} && make install""".format(local_dir=i.local_dir, num_cores=self.num_cores(),CC=self.CC, CXX=self.CXX, ext_dir=self.extDirLoc)
        cmd = " ".join(cmd.split())
        #branchName = "r3.0.0"
        branchName = "07d4243445b5f0f333bf0ee9b3f482e74adf67a4" #r3.0.1
        
        self.__buildFromGitTag(i, cmd, branchName)
    
    def cppcms(self):
        i = self.__path('cppcms')
        cmd = "mkdir -p build && cd build && CC={CC} CXX={CXX} cmake -DCMAKE_INSTALL_PREFIX:PATH={local_dir} .. && make -j {num_cores} install".format(local_dir=shellquote(i.local_dir), num_cores=self.num_cores(), CC=self.CC, CXX=self.CXX)  
        if(sys.platform == "darwin"):
            cmd += " && install_name_tool -change libbooster.0.dylib {local_dir}/lib/libbooster.0.dylib {local_dir}/lib/libcppcms.1.dylib".format(local_dir=shellquote(i.local_dir), num_cores=self.num_cores())
        cmd = " ".join(cmd.split())
        self.__build(i, cmd)

    def armadillo(self):
        i = self.__path('armadillo')
        cmd = "mkdir -p build && cd build && CC={CC} CXX={CXX} cmake -DCMAKE_INSTALL_PREFIX:PATH={local_dir} .. && make -j {num_cores} install".format(
            local_dir=shellquote(i.local_dir), num_cores=self.num_cores(), CC=self.CC, CXX=self.CXX)
        cmd = " ".join(cmd.split())
        self.__build(i, cmd)



    def zi_lib(self):
        self.__git(self.__path('zi_lib'))
        
    def pstreams(self):
        pspaths = self.__path('pstreams')
        os.mkdir(pspaths.local_dir)
        gitCmd = "git clone {url} {d}".format(url=pspaths.url, d=shellquote(os.path.join(pspaths.local_dir, "pstreams")))
        Utils.run(gitCmd)

    def cppitertools(self):
        cppitpaths = self.__path('cppitertools')
        os.mkdir(cppitpaths.local_dir)
        gitCmd = "git clone {url} {d}".format(url=cppitpaths.url, d=shellquote(os.path.join(cppitpaths.local_dir, "cppitertools")))
        Utils.run(gitCmd)
        cmd = "cd {d} && git checkout d4f79321842dd584f799a7d51d3e066a2cdb7cac".format(d=shellquote(os.path.join(cppitpaths.local_dir, "cppitertools")))
        Utils.run(cmd)
    
    def dlib(self):
        i = self.__path('dlib')
        cmd = """
mkdir {local_dir} &&
cp -a * {local_dir}/
""".format(local_dir=shellquote(i.local_dir), num_cores=self.num_cores())
        cmd = " ".join(cmd.split('\n'))
        self.__build(i, cmd)
        
    def libsvm(self):
        i = self.__path('libsvm')
        cmd = "make && make lib && mkdir -p {local_dir} && cp -a * {local_dir}".format(
            local_dir=shellquote(i.local_dir))
        self.__build(i, cmd)

    def catch(self):
        self.__git(self.__path('catch'))


def ubuntu(self):
        pkgs = """libbz2-dev python2.7-dev cmake libpcre3-dev zlib1g-dev libgcrypt11-dev libicu-dev
python doxygen doxygen-gui auctex xindy graphviz libcurl4-openssl-dev""".split()



def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--compfile', type=str, nargs=1)
    parser.add_argument('--libs', type=str, help="The libraries to install")
    parser.add_argument('--printLibs', action = "store_true", help="Print Available Libs")
    parser.add_argument('--forceUpdate', action = "store_true", help="Remove already installed libs and re-install")
    parser.add_argument('--updateBibProjects', type = str, help="Remove already installed libs and re-install")
    parser.add_argument('--CC', type=str, nargs=1)
    parser.add_argument('--CXX', type=str, nargs=1)
    parser.add_argument('--instRPackageName',type=str, nargs=1)
    parser.add_argument('--instRPackageSource',type=str, nargs=1) 
    parser.add_argument('--addBashCompletion', dest = 'addBashCompletion', action = 'store_true')
    parser.add_argument('--numCores', type=str)
    return parser.parse_args()

def main():
    args = parse_args()
    s = Setup(args)
    ccWhich = Utils.which(s.CC)
    cxxWhich = Utils.which(s.CXX)
    cmakeWhich = Utils.which("cmake")
    if not ccWhich or not cxxWhich or not cmakeWhich:
        if not ccWhich:
            print CT.boldRed("Could not find c compiler " + CT.purple + s.CC)
            if args.compfile:
                print "Change CC in " + args.compfile
            else:
                print "Can supply another c compiler by using -CC [option] or by defining bash environmental CC "
            print ""
        if not cxxWhich:
            print CT.boldRed("Could not find c++ compiler " + CT.purple + s.CXX)
            if args.compfile:
                print "Change CXX in " + args.compfile
            else:
                print "Can supply another c++ compiler by using -CXX [option] or by defining bash environmental CXX "
            print ""
        if not cmakeWhich:
            print CT.boldRed("Could not find " + CT.purple + "cmake")
            if Utils.isMac():
                print "If you have brew install via, brew update && brew install cmake, otherwise you can follow instructions from http://www.cmake.org/install/"
            else:
                print "On ubuntu to install latest cmake do the following"
                print "sudo add-apt-repository ppa:george-edison55/cmake-3.x"
                print "sudo apt-get update"
                print "sudo apt-get install cmake"
        return 1
        
    
    if(args.instRPackageName):
        s.installRPackageName(args.instRPackageName[0])
        return 0
    if(args.instRPackageSource):
        s.installRPackageSource(args.instRPackageSource[0])
        return 0
    if args.updateBibProjects:
        projectsSplit = args.updateBibProjects.split(",")
        s.updateBibProjects(projectsSplit)
        return 0
    if args.printLibs:
        s.printAvailableSetUps()
    elif args.addBashCompletion:
        if(os.path.isdir("./bashCompletes")):
            cmd = "cat bashCompletes/* >> ~/.bash_completion"
            Utils.run(cmd)
        if(os.path.isdir("./bash_completion.d")):
            cmd = "cat bash_completion.d/* >> ~/.bash_completion"
            Utils.run(cmd)
    else:
        if len(s.setUpsNeeded) == 0:
            s.printAvailableSetUps()
            return 1
        else:
            s.setup()
            return 0

main()
