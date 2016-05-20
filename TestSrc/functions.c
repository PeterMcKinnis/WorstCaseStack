

#include "alloc.h"

static int static1(char* str, int len);
int static2(float a, float b);
void static3(int a);
void static4(int a);
int static5(int a);
void recursive1(void);
void recursive2a(void);
void recursive2b(void);
void recursive2c(void);
void recursive2d(void);
void indirect1(int i);
void indirect2(void);
void indirect3(int i, int offset);
void indirect4(int i);
void inline_asm1(int i);

void extern_prv_fxn1(void);
typedef void(*action)(void);
typedef void(*action_int)(int);



static int static1(char* str, int len) {
	STACK_ALLOC(240);
	return len;
}

int static2(float a, float b) {
	STACK_ALLOC(140);
	return (int)b;
}

void static3(int a) {
	static1("Hi", 2);
	static2(1.5,3.5);
}

void static4(int a) {
	static1("Hi", 2);
	static2(1.5, 3.5);
	static3(5);
}

int static5(int a) {
	extern_prv_fxn1();
	extern_prv_fxn1();
}


void recursive1(void) {
	STACK_ALLOC(40);
	recursive1();
}

void recursive2a(void) {
	STACK_ALLOC(8);
	recursive2b();
}

void recursive2b(void) {
	STACK_ALLOC(144);
	recursive2c();
}

void recursive2c(void) {
	STACK_ALLOC(990);
	recursive2d();
}

void recursive2d(void) {
	STACK_ALLOC(120);
	recursive2a();
}


typedef void(*action)(void);
typedef void(*action_int)(int);


void indirect1(int i) {

	// Use of function pointers
	action_int a;

	if (i) {
		a = static3;
	}
	else {
		a = static4;
	}

	a(i);

}

void indirect2(void) {

	// Call A function at address 0x1205
	int x = 0x1205;
	action a = (action*)x;
	a();

}

void indirect3(int i, int offset) {

	// Use of function pointer math (un
	action_int a;

	if (a) {
		a = &static3;
	}
	else {
		a = &static4;
	}

	a = (action_int)(((char *)a) + offset);

	a(i);

}

void indirect4(int i) {

	// Use of function pointer math (un
	action_int a = static3;
	a(i);

}

void function_with_really_long_name_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA(int i) {

}

// There are multiple definitions of this in multiple files
void static prv_fxn1(void){
	STACK_ALLOC(100);
}

void functions_prv_fxn1(void) {
	prv_fxn1();
}

int main(void) {
	static1("Hello", 5);
	static2(11.3, 12.3);
	static3(5);
	static4(6);
	static5(7);
	recursive1();
	recursive2a();
	recursive2b();
	recursive2c();
	recursive2d();
	indirect1(5);
	indirect1(0);
	indirect2();
	indirect3(8,9);
	
	functions_prv_fxn1(); // This should use about  100 bytes of the stack
	extern_prv_fxn1();    // This should use about 1000 bytes of the stack
	return 0;
}

int main3(void) {
	main();
}

