.SUFFIXES = .c .o

OPTFLAGS = -g

CPX_INC = -I../IBM/ILOG/CPLEX_Studio221/cplex/include/ilcplex/
DBGFLAGS =  $(OPTFLAGS) -I. $(CPX_INC)
CFLAGS = $(DBGFLAGS) 
CPPFLAGS = $(DBGFLAGS) 

CPX_LIB = -L../IBM/ILOG/CPLEX_Studio221/cplex/lib/x86-64_linux/static_pic -lcplex -lm -lpthread

CPP=g++
#CPP = /cygdrive/c/MinGW/bin/g++
CC=gcc
#CC = /cygdrive/c/MinGW/bin/gcc

.c.o:
	$(CC) $(CFLAGS) -o $@ -c $< 

.cpp.o:
	$(CPP) $(CPPFLAGS) -o $@ -c $<

OBJ_FILES = fctgen.o

OBJ_FILES2 = fctgen2.o

fctpdp: $(OBJ_FILES)
	$(CPP) $(OPTFLAGS) -o fctpdp.exe $(OBJ_FILES) $(CPX_LIB)

fctgen: fctgen.o
	$(CPP) $(OPTFLAGS) -o fctgen.exe $(OBJ_FILES) $(CPX_LIB)

fctgen2: fctgen2.o
	$(CPP) $(OPTFLAGS) -o fctgen2.exe $(OBJ_FILES2) $(CPX_LIB)

clean:
	rm -f fctpdp.exe *.o
