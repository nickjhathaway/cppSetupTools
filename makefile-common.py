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
