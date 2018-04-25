

CC=arm-none-eabi-gcc
CFLAGS=-c -gdwarf-3 -fstack-usage -fdump-rtl-dfinish
LDFLAGS= -Wall --specs=nosys.specs
SOURCES=functions.c my_lib.c no_functions.c
OBJECTS=$(SOURCES:.c=.o)
EXECUTABLE=test.exe

all: $(SOURCES) $(EXECUTABLE) 

$(EXECUTABLE): $(OBJECTS) 
	$(CC) $(LDFLAGS) $(OBJECTS) -o $@

.c.o:
	$(CC) $(CFLAGS) $< -o $@

clean:
	rm *.o *.c.* *.su