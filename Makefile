libbeal.so: beal.cc
	g++ -Wall -O3 -fPIC -shared -o $@ $?
