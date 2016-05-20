

#define STACK_ALLOC(x) {     \
	volatile char mem[x] = {}; \
	mem[0] = mem[x-1];       \
}
