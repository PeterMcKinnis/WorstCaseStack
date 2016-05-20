
#include "alloc.h"

void extern_prv_fxn1(void);
void static prv_fxn1(void);

void extern_prv_fxn1(void) {
	prv_fxn1();
}

// There are multiple definitions of this in multiple files
void static prv_fxn1(void){
	STACK_ALLOC(1000);
}