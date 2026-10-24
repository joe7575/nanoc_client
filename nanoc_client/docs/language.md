# NanoC Code Generation Prompt

You are generating code for **NanoC**, a simple C-like language for embedded systems.

## CRITICAL RULES

1. Use `func` keyword for ALL functions, NOT `void`
2. Use `//` for comments, NOT `/* */` or `rem`
3. Use `{ }` for blocks, NOT `begin/end`
4. Use `==` for equality, `!=` for inequality
5. Keywords are lowercase: `func`, `int32`, `return`, `if`, `else`, `for`, `while`
6. String variables are declared with `str8`; do NOT use the old BASIC `$` suffix for variables and built-in functions (`name$`, `left$()`). Host functions whose name contains `$` (e.g. `sys$()`) keep it.
7. No semicolons at end of statements (but `;` can separate multiple statements on one line)
8. No floating-point - integers only (int32)

## FORBIDDEN - NEVER USE

- `goto`, `gosub` - use `func` instead
- `void` - use `func` without return type
- `let`, `dim` - use `int32`, `str8`
- `rem` - use `//
- `then`, `endif`, `loop`, `next` - use `{ }`
- `data`, `read`, `restore`
- `get1`, `get2`, `get4`, `set1`, `set2`, `set4` - use `u8`, `u16`, `u32`

## SYNTAX REFERENCE

### Variable Declarations
```c
int32 x = 0           // signed 32-bit integer
int32 x = 0xFF        // hex literal (0x prefix supported)
int32 arr[100]        // array of 100 elements
str8 name = "Hello"   // string
const MAX = 0x100     // constant can also use hex literals
```

### Array Reference Parameters
Use `int32[]` in function parameters to pass arrays by reference:
```c
func processData(int32[] buffer, int32 count) {
    // buffer refers to the original array - modifications affect it
    buffer[0] = 42
}
```

### Array References (C-style)
Array names without `[]` are passed as references (like C pointers):
```c
int32 src[10]
int32 dst[10]
copy(dst, 0, src, 0, 40)  // Copy 40 bytes
```

### Functions
```c
// Void function (no return value)
func my_handler(int32 param) {
    printf("param=%d\n", param)
}

// Function with return value
func int32 add(int32 a, int32 b) {
    return a + b
}

// Array reference parameter (passed by reference)
func int32 sumArray(int32[] arr, int32 size) {
    int32 sum = 0
    for i = 0 to size - 1 {
        sum = sum + arr[i]
    }
    return sum
}

// Function that modifies array
func clearArray(int32[] arr, int32 size) {
    for i = 0 to size - 1 {
        arr[i] = 0
    }
}

// Call in expression
int32 result = add(10, 20)

// Call with array reference
int32 data[10]
int32 total = sumArray(data, 10)  // Pass array by reference
clearArray(data, 10)              // Modifies original array
```

### Control Structures
```c
// if-else
if (x > 0) {
    y = 1
} else {
    y = 0
}

// else if (any number, final else optional)
if (x > 10) {
    y = 2
} else if (x > 0) {
    y = 1
} else {
    y = 0
}

// for loop
for i = 1 to 10 {
    printf("%d\n", i)
}

for i = 10 to 0 step -1 {
    printf("%d\n", i)
}

// while loop
while (x > 0) {
    x--
}

// break leaves the innermost for/while loop (compile error outside a loop)
while (1) {
    if (done) {
        break
    }
}

// dispatch (indexed function dispatch, 0-based)
dispatch(state) {
    handler_idle,
    handler_running,
    handler_error
}
// Calls handler_idle() if state==0, handler_running() if state==1, etc.
// Out-of-range values are silently skipped.

// dispatch (inline) - code runs in current scope
// case values: numbers or consts 0..31, any order, gaps skipped
dispatch(id) {
    0: printf("idle\n")
    1: printf("run %d\n", val)
    2: {
        int32 sum = d1 + d2
        printf("error %d\n", sum)
    }
}
```

### Operators
```
Arithmetic: + - * / % (or mod)
Bitwise:    & | ^ << >>
Comparison: == != < <= > >=
Logical:    and or not
Increment:  ++ --
```

### Output
```c
printf("Value: %d\n", x)      // %d=signed int, %u=unsigned int, %s=string, %h=hex
printf("Name: %s\n", name)    // string output
// Escape sequences: \n=newline, \t=tab, \a=BEL/end-of-output, \\=backslash
```

### String Functions
```c
len(s)                     // length
left(s, n)                 // first n chars
right(s, n)                // last n chars
mid(s, start, len)         // substring (0-based)
str(n)                     // int to string
hex(n)                     // int to hex string
instr(start, s, find)      // find substring (0-based, -1 if not found)
string(n, char)            // repeat first char n times
```

**Note:** `mid` and `instr` use 0-based indexing (like C).

### Byte Access (array memory)
```c
u8(arr, offset)            // read byte
u8(arr, offset, value)     // write byte
u16(arr, offset)           // read 16-bit
u16(arr, offset, value)    // write 16-bit
u32(arr, offset)           // read 32-bit
u32(arr, offset, value)    // write 32-bit
str2arr(arr, offset, s)    // write string incl. terminating 0
arr2str(arr, offset)       // read 0-terminated string
```

### Other
```c
rnd(n)                     // random 0 to n-1
copy(dst, doff, src, soff, len)  // copy bytes (destination first!)
end                        // terminate program
reti                       // return from interrupt handler
breakpoint()               // breakpoint in the source code (debugger)
NULL                       // null pointer constant
```

## PROGRAM STRUCTURE

```c
// 1. Function definitions FIRST (before main code)
func int32 helper(int32 x) {
    return x * 2
}

func process(int32 data) {
    int32 result = helper(data)
    printf("Result: %d\n", result)
}

// 2. Global variables
int32 counter = 0
int32 buffer[100]

// 3. Main program code
printf("Starting...\n")
process(42)
counter++
printf("Counter: %d\n", counter)
end
```

## LOCAL vs GLOBAL VARIABLES

- Variables declared **outside** functions = GLOBAL
- Variables declared **inside** functions = LOCAL (stack-based, reentrant)
- Parameters are always LOCAL

```c
int32 global_var = 0    // GLOBAL

func example(int32 param) {    // param is LOCAL
    int32 local_var = 10       // LOCAL
    global_var = param         // access GLOBAL
}
```

## LIMITATIONS

- Variable names: max 15 chars
- Line length: max 127 chars
- Nested calls: max 8 levels
- Parameters: max 8 per function
- No float/double
- No multi-dim arrays
- At most 2 string function results (`left()`, `mid()`, `hex()`, `+`, ...) per statement; use `str8` variables for more
- No function-local arrays (declare arrays globally or pass via `int32[]` parameter)
- `arr[i]++` not supported, use `arr[i] = arr[i] + 1`
