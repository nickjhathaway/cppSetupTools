


#gtkmm library, should have 3.0 install and .pc file should be in PKG_CONFIG_PATH  
ifeq ($(USE_GTKMM),1)
	LD_FLAGS += `pkg-config gtkmm-3.0 --libs`
	COMLIBS += `pkg-config gtkmm-3.0 --cflags`
endif

#ml_pack
ifeq ($(USE_MLPACK),1)
	ifeq ($(UNAME_S),Darwin)
    	LD_FLAGS += -llapack  -lcblas # non-threaded
	else
   		LD_FLAGS += -llapack -lf77blas -lcblas -latlas # non-threaded
	endif
endif

#qt5
ifeq ($(USE_QT5),1)
	ifeq ($(UNAME_S),Darwin)
		LD_FLAGS += -Wl,-rpath,/usr/local/opt/qt5/lib \
	 				-L/usr/local/opt/qt5/lib \
	 				-lQt5UiTools
    	COMLIBS += -I/usr/local/opt/qt5/include
	endif
endif

# from http://stackoverflow.com/a/18258352
rwildcard=$(foreach d,$(wildcard $1*),$(call rwildcard,$d/,$2) $(filter $(subst *,%,$2),$d))
