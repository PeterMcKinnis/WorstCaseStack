# Worst Case Stack

## Overview
This program is used to do static stack analysis on C source code to determine the maximum stack space used by each function.  Source must be compiled using gcc with a number of special flags (see below for details)

## Useage
1. compile *.c sources using gcc and the flags `-c`, `-fdump-rtl-dfinish` and `-fstack-usage`
2. Run the script python `wcs.py`

```
gcc -c -fdump-rtl-dfinish -fstack-usage main.c my_library.c other.c
wcs.py
```

**Note:** When running `wcs.py` the current working directory must contain all the relevant input files.


## Dependencies
This script requires python 3.  It was written and tested using version 3.4.3

## Inputs - Files from gcc.
The script will search the current directory for sets of files with the names `<name>.o`, `<name>.su` and `<name>.c.270r.dfinish`. If all three are found the script will calculate the worst case stack for every function in the `<name>.c`.

See the usage section for information about how to generate these files.

## Inputs - Manual Stack Usage Files
The scripts also look in files ending with *.msu.  These files should contain a whitespace delimited table with function names in the first column, and a decimal integer with the worst case stack usage in the second line 

```
my_function 20
do_something 120
__exit 144
```

Every line must contain a function / stack pair (empty lines are not permitted).  These files can be useful for specifying the worst case stack for functions for which the c-source is not available but the stack usage is known by other means such as inspecting the assembly or run-time testing.

## Output
The script will output a list of functions in a table with the following columns:
1. **Translation Unit** (e.g. the name of the file where the function is implemented)
2. **Function Name**
3. **Stack** Either the maximum number of bytes during a call to this function (including nested calls at all depths)
or the string `unbounded` if the maximum cannot be determined because some function in the call tree is recursively defined or makes calls via function pointer.
4. **Unresolved Dependancies** A list functions that are called somewhere in the call tree for which there is no
definition in any of the given input files.

## Known Limitations:
1. `wcs.py` can only determine stack usage from `*.c` source.  Calls to compiled libraries (e.g. libc.a) or to assembly functions will result in `unbounded` (e.g. unknown) stack usage.
2. Functions compiled with the `weak` attribute will crash this script
3. The actual worst case stack may be greater than reported by this function if outside actors modify the stack.  Common offenders are:
    1. Interrupt handlers
    2. Operating system context changes
4. The use of inline assembly will result in potentially incorrect results.  Specifically, if a function uses inline assembly to load or store from the stack, modify the stack pointer, or branch to code that does likewise, expect incorrect results.  

**The script has no way to detect situations 3 and 4.  In the presence of these conditions the script will complete successfully.  Use caution.**

## Notes
5. This script assumes little endian byte ordering for object files.  If you are compiling for a big-endian system set the `byte_order` variable to `">"` in the file `elf.py`

```
byte_order = ">" 
```
