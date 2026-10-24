# NanoC Reference Manual

## Table of Contents

- [NanoC Reference Manual](#nanoc-reference-manual)
  - [Table of Contents](#table-of-contents)
  - [Introduction](#introduction)
    - [Character Set](#character-set)
    - [Comments](#comments)
    - [Multiple Statements per Line](#multiple-statements-per-line)
    - [Constants](#constants)
    - [Variables](#variables)
    - [Array Variables](#array-variables)
    - [Expressions and Operators](#expressions-and-operators)
    - [String Operations](#string-operations)
  - [Data Types](#data-types)
  - [Variable Declarations](#variable-declarations)
    - [int32](#int32)
    - [str8](#str8)
  - [Functions](#functions)
    - [Function Definition](#function-definition)
    - [Array Reference Parameters](#array-reference-parameters)
    - [Function with Return Value](#function-with-return-value)
    - [Local Variables](#local-variables)
    - [return Statement](#return-statement)
  - [Control Structures](#control-structures)
    - [if...else](#ifelse)
    - [for Loop](#for-loop)
    - [while Loop](#while-loop)
    - [break](#break)
    - [dispatch (Indexed Dispatch)](#dispatch-indexed-dispatch)
      - [Function Dispatch](#function-dispatch)
      - [Inline Dispatch](#inline-dispatch)
  - [Statements](#statements)
    - [const](#const)
    - [end](#end)
    - [printf](#printf)
    - [reti](#reti)
    - [breakpoint](#breakpoint)
  - [Built-in Functions](#built-in-functions)
    - [Numeric Functions](#numeric-functions)
    - [String Functions](#string-functions)
    - [Byte Access Functions](#byte-access-functions)
    - [Memory Functions](#memory-functions)
  - [Increment and Decrement Operators](#increment-and-decrement-operators)
  - [Example Program](#example-program)
  - [Limitations](#limitations)

---

## Introduction

NanoC is a simple C-like programming language designed for embedded systems and resource-constrained environments. It compiles to bytecode that runs on the NanoVM, a lightweight virtual machine.

NanoC is derived from NanoBasic but uses C-style syntax with curly braces, typed variable declarations, and user-defined functions with local variables.

### Character Set

NanoC supports the ASCII character set, including upper and lower case letters, digits 0-9, and special characters. NanoC is **case-sensitive** for both keywords and variable names (all keywords are lowercase).

### Comments

NanoC supports C-style single-line comments:

```c
// This is a comment
int32 x = 10  // inline comment
```

A special directive comment `//#line N` resets the compiler's internal line
counter to `N`, so that subsequent error messages refer to that numbering.
This is useful when user code is embedded into a larger generated program and
errors should point to the user's own source lines. Older firmware treats it as
a normal comment (forward compatible).

```c
//#line 1
// the next line is reported as line 1 on error
```

### Multiple Statements per Line

Multiple statements can be written on one line, separated by `;`:

```c
x = 1; y = 2; z = 3
```

Semicolons are **not** required at the end of statements.

### Constants

NanoC supports integer and string constants:

```c
1234        // decimal integer constant
-42         // negative integer
0xFF        // hexadecimal integer constant (0x prefix, case-insensitive)
0x1A2B      // larger hex constant
"Hello"     // string constant
```

Numeric constants are 32-bit signed integers in the range -2,147,483,648 to 2,147,483,647. Hexadecimal literals use the `0x` or `0X` prefix.

Named constants are defined with `const`:

```c
const MAX_SIZE = 100
const PI_X1000 = 3141
```

**NULL** is a special constant representing a null pointer:

```c
copy(buffer, 0, NULL, 0, 10)  // NULL as source reference
```

### Variables

Variable names must begin with a letter and may contain letters, digits, and underscores. Only the first 15 characters are significant.

String variables are declared with `str8`:

```c
int32 count = 0
str8 name = "Hello"
```

**Note:** Older scripts use the BASIC-style `$` suffix for string variables and string functions (`name$`, `left$()`, `hex$()`, ...). This form is still supported, so existing scripts keep working. `name` and `name$` are two different variables, so do not mix both forms for the same name.

### Array Variables

Arrays are declared with a size in brackets:

```c
int32 buffer[100]    // array of 100 elements (indices 0-99)
int32 data[10]       // 32-bit array
```

Array elements are accessed with bracket notation:

```c
buffer[0] = 42
x = data[5]
```

### Expressions and Operators

| Category    | Operator | Description          |
|-------------|----------|----------------------|
| Arithmetic  | `+`      | Addition             |
|             | `-`      | Subtraction          |
|             | `*`      | Multiplication       |
|             | `/`      | Division             |
|             | `%`, `mod` | Modulus            |
| Bitwise     | `&`      | Bitwise AND          |
|             | `\|`     | Bitwise OR           |
|             | `^`      | Bitwise XOR          |
|             | `<<`     | Shift left           |
|             | `>>`     | Shift right          |
| Relational  | `==`     | Equal                |
|             | `!=`     | Not equal            |
|             | `<`      | Less than            |
|             | `<=`     | Less than or equal   |
|             | `>`      | Greater than         |
|             | `>=`     | Greater than or equal|
| Logical     | `and`    | Logical AND          |
|             | `or`     | Logical OR           |
|             | `not`    | Logical NOT          |
| Increment   | `++`     | Increment            |
|             | `--`     | Decrement            |

**Operator Precedence** (highest to lowest):

1. `()` Parentheses
2. `-` (unary), `not`
3. `*`, `/`, `%`, `mod`
4. `+`, `-`
5. `<<`, `>>`
6. `&`
7. `^`
8. `|`
9. `==`, `!=`, `<`, `<=`, `>`, `>=`
10. `and`
11. `or`

### String Operations

Strings can be concatenated with `+`:

```c
str8 a = "Hello"
str8 b = " World"
str8 c = a + b    // "Hello World"
```

String comparisons use relational operators:

```c
if (a == "Hello") { ... }
if (a < b) { ... }
```

---

## Data Types

| Type       | Description                                    |
|------------|------------------------------------------------|
| `int32`    | Signed 32-bit integer (-2,147,483,648 to 2,147,483,647) |
| `int32[]`  | Array of 32-bit integers                       |
| `int32[]`  | Array reference parameter (in function definitions) |
| `str8`     | String (up to 120 characters)                  |
| `const`    | Compile-time numeric constant                  |

---

## Variable Declarations

### int32

Declares a signed 32-bit integer variable or array:

```c
int32 x = 0
int32 count = 100
int32 negative = -42
int32 buffer[100]    // array of 100 elements
int32 data[10]       // array of 10 elements
```

### str8

Declares a string variable:

```c
str8 name = "Hello"
str8 empty = ""
```

`str8` function parameters are read-only.

---

## Functions

### Function Definition

Functions are defined with the `func` keyword. Parameters are typed:

```c
func my_function(int32 param1, int32 param2) {
    // function body
    // param1 and param2 are LOCAL variables
}
```

**Note:** Functions can be defined anywhere in the file. Forward references are automatically resolved.

### Array Reference Parameters

Arrays can be passed to functions by reference using `int32[]` syntax:

```c
// Function that modifies array elements
func doubleArray(int32[] arr, int32 size) {
    for i = 0 to size - 1 {
        arr[i] = arr[i] * 2
    }
}

// Function that reads array elements
func int32 sumArray(int32[] arr, int32 size) {
    int32 sum = 0
    for i = 0 to size - 1 {
        sum = sum + arr[i]
    }
    return sum
}

// Usage
int32 data[5]
data[0] = 1
data[1] = 2
data[2] = 3

printf("Sum before: %d\n", sumArray(data, 3))  // Output: 6
doubleArray(data, 3)
printf("Sum after: %d\n", sumArray(data, 3))   // Output: 12
```

**Note:** Array parameters are always passed by reference. Modifications inside the function affect the original array.

### Function with Return Value

To return a value, specify the return type after `func`:

```c
func int32 add(int32 a, int32 b) {
    return a + b
}

func int32 max(int32 a, int32 b) {
    if (a > b) {
        return a
    }
    return b
}
```

A call with a return value can be used in an expression, e.g.
`int32 x = add(1, 2) * 3`. For calls in expressions the function must be
defined before the call (recursion works because the return type is known at
the definition). Plain statement calls may still reference functions defined
later in the file.

### Local Variables

All variables declared inside a function are **local** (stack-based):

```c
func calculate(int32 input) {
    int32 temp = input * 2    // LOCAL variable
    int32 result = temp + 10  // LOCAL variable
    printf("Result: %d\n", result)
}
```

Global variables remain accessible from within functions:

```c
int32 counter = 0   // GLOBAL

func increment() {
    counter++       // accesses GLOBAL counter
}
```

### return Statement

The `return` statement exits a function and optionally returns a value:

```c
func int32 square(int32 n) {
    return n * n
}

func on_event(int32 id) {
    if (id == 0) {
        return        // early exit, no return value
    }
    printf("id=%d\n", id)
}
```

---

## Control Structures

### if...else

```c
if (expression) {
    // statements
}

if (expression) {
    // statements
} else {
    // statements
}

if (expression) {
    // statements
} else if (expression) {
    // statements
} else {
    // statements
}

// Single-line form
if (x > 0) { y = 1 } else { y = 0 }
```

`else if` can be chained any number of times; the final `else` is optional.

### for Loop

```c
for variable = start to end {
    // statements
}

for variable = start to end step increment {
    // statements
}
```

Examples:

```c
for i = 1 to 10 {
    printf("%d\n", i)
}

for i = 10 to 0 step -1 {
    printf("Countdown: %d\n", i)
}
```

An empty range is skipped: with a positive step the body does not run when
`start > end`; with a negative step it does not run when `start < end`.
This works for global and function-local loop variables.

### while Loop

```c
while (expression) {
    // statements
}
```

Example:

```c
int32 i = 0
while (i < 10) {
    printf("%d\n", i)
    i++
}
```

### break

Leaves the innermost `for` or `while` loop, like in C. Outside a loop `break` is a compile error.

```c
for i = 0 to 99 {
    if (buffer[i] == 0) {
        break
    }
}
```

### dispatch (Indexed Dispatch)

#### Function Dispatch

Calls a function based on a 0-based index (like GOSUB). If the index is out of range, the dispatch is silently skipped.

```c
dispatch(expression) {
    function_name_0,
    function_name_1,
    function_name_2
}
```

#### Inline Dispatch

Executes the code of the matching case value. The code runs in the current scope with access to all local variables and parameters. If no case matches, the dispatch is silently skipped.

```c
dispatch(expression) {
    0: single_statement
    1: another_statement
    2: {
        multi_line_block
    }
}
```

Example:

```c
func on_event(int32 id, int32 d1, int32 d2) {
    dispatch(id) {
        0: printf("idle\\n")
        1: printf("run d1=%d d2=%d\\n", d1, d2)
        2: {
            int32 sum = d1 + d2
            printf("error sum=%d\\n", sum)
        }
    }
}
```

Case values can be numbers or constants defined with `const` (before the `dispatch`) in the range 0..31. They may appear in any order and with gaps; the compiler builds the jump table, so there is no runtime cost. Gaps behave like out-of-range values (skipped). Duplicate values are a compile error.

```c
const IDLE = 0
const RUN = 1
const ERROR = 3

dispatch(state) {
    ERROR: printf("error\\n")
    IDLE: printf("idle\\n")
    RUN: printf("running\\n")
}
```
---

## Statements

### const

Defines a compile-time constant:

```c
const MAX_SIZE = 100
const BUFFER_LEN = 256

int32 buffer[MAX_SIZE]
```

### end

Terminates program execution:

```c
printf("Done!\n")
end
```

### printf

Formatted output (C-style):

```c
printf("Value: %d\n", x)
printf("Unsigned: %u\n", x)
printf("Name: %s, Age: %d\n", name, age)
printf("Hex: %h\n", value)
```

Format specifiers:
- `%d` - decimal integer (signed)
- `%u` - decimal integer (unsigned)
- `%h` - hexadecimal integer (uppercase)
- `%s` - string
- `%%` - literal percent sign

Escape sequences:
- `\n` - newline
- `\t` - tab
- `\a` - BEL / end-of-output signal
- `\\` - literal backslash

### reti

Return from interrupt handler. Signals the host system that interrupt processing is complete:

```c
func on_can(int32 id, int32 data) {
    printf("CAN: id=%d, data=%d\n", id, data)
    reti
}
```

### breakpoint

Breakpoint in the source code: the VM returns `NB_BREAK` to the host with the line number on the parameter stack. What happens next is up to the host (e.g. halt in the debugger or ignore it).

```c
if (error_count > 3) {
    breakpoint()
}
```

---

## Built-in Functions

### Numeric Functions

| Function | Description |
|----------|-------------|
| `rnd(n)` | Random number from 0 to n-1 |
| `abs(n)` | Absolute value of n |

```c
int32 dice = rnd(6) + 1   // 1-6
int32 dist = abs(a - b)   // absolute difference
```

### String Functions

| Function | Description |
|----------|-------------|
| `len(s)` | Length of string |
| `left(s, n)` | Left n characters |
| `right(s, n)` | Right n characters |
| `mid(s, start, len)` | Substring (0-based index) |
| `str(n)` | Number to string |
| `hex(n)` | Number to hex string |
| `instr(start, s, find)` | Find substring (0-based, returns -1 if not found) |
| `string(n, char)` | Repeat first char of string n times |

**Note:** `mid` and `instr` use 0-based indexing (first character is position 0).

**Important:** The return value of a string function must be used, e.g. assigned to a `str8` variable. Calling it as a standalone statement causes a syntax error:

```c
str8 result = left(s, 5)    // OK
left(s, 5)                  // ERROR: syntax error
```

Examples:

```c
str8 s = "Hello World"
int32 l = len(s)               // 11
str8 h = left(s, 5)            // "Hello"
str8 w = right(s, 5)           // "World"
str8 o = mid(s, 6, 5)          // "World" (pos 6 = 'W')
int32 pos = instr(0, s, "o")   // 4 (first 'o' at position 4)
int32 nf = instr(0, s, "xyz")  // -1 (not found)
str8 num = str(42)             // "42"
str8 hx = hex(255)             // "FF"

// Repeat character
str8 star = "*"
str8 line = string(10, star)   // "**********"
```

### Byte Access Functions

These functions allow direct byte/word/dword access to array memory:

| Function | Description |
|----------|-------------|
| `u8(arr, idx)` | Read byte at offset idx |
| `u8(arr, idx, val)` | Write byte at offset idx |
| `u16(arr, idx)` | Read 16-bit word at offset idx |
| `u16(arr, idx, val)` | Write 16-bit word at offset idx |
| `u32(arr, idx)` | Read 32-bit dword at byte offset idx |
| `u32(arr, idx, val)` | Write 32-bit dword at byte offset idx |

**Note:** `idx` is always a **byte offset** for all three functions (u8, u16, u32).

```c
int32 buffer[10]          // 40 bytes (10 * 4)

u8(buffer, 0, 0xFF)       // Write byte at offset 0
u8(buffer, 1, 0xAB)       // Write byte at offset 1
int32 b = u8(buffer, 0)   // Read byte (255)

u16(buffer, 0, 0x1234)    // Write word at byte offset 0
u16(buffer, 2, 0x5678)    // Write word at byte offset 2
int32 w = u16(buffer, 0)  // Read word

u32(buffer, 0, 0xDEADBEEF) // Write dword at byte offset 0
u32(buffer, 4, 0x12345678) // Write dword at byte offset 4
int32 d = u32(buffer, 0)   // Read dword
```

Strings and arrays:

| Function | Description |
|----------|-------------|
| `str2arr(arr, idx, s)` | Write string `s` incl. terminating 0 at byte offset idx (`len(s) + 1` bytes) |
| `arr2str(arr, idx)` | Read a 0-terminated string from byte offset idx (ends at the array end if there is no 0) |

```c
int32 rsp[8]
str2arr(rsp, 3, "CANbridge")     // bytes 3..12: "CANbridge" + 0
printf("%s\n", arr2str(rsp, 3))  // CANbridge
```

### Memory Functions

| Function | Description |
|----------|-------------|
| `copy(dst, doff, src, soff, len)` | Copy len bytes from src+soff to dst+doff (destination first!) |
| `free()` | Print free memory info |

Array names without `[]` are passed as references:

```c
int32 src[10]
int32 dst[10]

copy(dst, 0, src, 0, 40)  // Copy 40 bytes from src to dst
```

---

## Increment and Decrement Operators

NanoC supports C-style increment and decrement for simple variables:

```c
int32 i = 0
i++      // i = 1
i++      // i = 2
i--      // i = 1
```

These work with both global and local variables, but **not** with array elements:

```c
arr[i]++              // NOT supported
arr[i] = arr[i] + 1   // Use this instead
```

---

## Example Program

```c
// Fibonacci sequence calculator

func int32 fib(int32 n) {
    if (n <= 1) {
        return n
    }
    int32 a = fib(n - 1)
    int32 b = fib(n - 2)
    return a + b
}

// Main program
printf("Fibonacci sequence:\n")
for i = 0 to 10 {
    int32 f = fib(i)
    printf("fib(%d) = %d\n", i, f)
}
end
```

---

## Limitations

- Variable names: max 15 characters
- Line length: max 127 characters
- Nested loops/calls: max 8 levels
- Parameters per function: max 8
- No floating-point numbers
- No multi-dimensional arrays
- No function-local array declarations (use global arrays or array reference parameters)
- A function used in an expression must be defined before the call; statement
  calls may use forward references.
- At most two temporary strings per statement: results of string functions and of `+` are kept in two alternating buffers, so a third one overwrites the first. Example: `printf("%s %s %s", left(s, 1), mid(s, 1, 1), right(s, 1))` prints the result of `right()` twice. Split the statement or assign intermediate results to `str8` variables.
