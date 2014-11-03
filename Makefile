libbeal.so: beal.cc
	g++ -Wall -fPIC -shared -o $@ $?
