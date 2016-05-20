__author__ = 'Peter'

import struct

byte_order = "<"


class Printable:
    def __repr__(self):
        from pprint import pformat

        return "<" + type(self).__name__ + "> " + pformat(vars(self), indent=4, width=1)


class Globals(Printable):
    pass


class EHeader(Printable):
    pass


class SHeader(Printable):
    pass


class Symbol(Printable):
    pass


# Puclic Functions
def read_symbols(file):
    g = Globals()
    g.file = file
    _read_file(g)
    return g.symbols


# Local Functions

def _read_file(g):
    # Load the file into memory
    with open(g.file, mode='rb') as fid:
        g.content = fid.read()

    # Read the header
    e = EHeader
    e.ident, e.type, e.machine, e.version, e.entry, e.phoff, e.shoff, e.flags, e.ehsize, e.phentsize, e.phnum, \
        e.shentsize, e.shnum, e.shstrndx = struct.unpack(byte_order + "16sHHIIIIIHHHHHH", g.content[:52])
    g.eHeader = e

    # Check the header
    _check_header(e)

    # Read Each Section
    _read_sections(g)

    # Read the symbols
    _read_symbol_table(g)


def _check_header(e_header):
    # Check that this is an obj file
    magic = e_header.ident[:4]
    if magic != b'\x7fELF':
        raise Exception("File {} does not seem to be in elf format")


def _read_sections(g):
    # Read in all the section headers
    g.sections = []
    for i in range(g.eHeader.shnum):
        # Read the section header
        offset = g.eHeader.shoff + i * g.eHeader.shentsize
        s = SHeader()
        s.offset, s.type, s.flags, s.addr, s.offset, s.size, s.link, s.info, s.addrAlign, s.entSize \
            = struct.unpack(byte_order + "IIIIIIIIII", g.content[offset:offset + 40])

        g.sections.append(s)


def _read_name(g, section_index, name_index):
    # Get the offset to the section
    offset = g.sections[section_index].offset

    # Read a bytes until null
    start = offset + name_index
    end = start
    while g.content[end]:
        end += 1

    # Convert to string
    return g.content[start:end].decode('utf-8')


_bind_names = {0: 'LOCAL', 1: 'GLOBAL', 2: 'WEAK'}
_type_names = {0: 'NOTYPE', 1: 'OBJECT', 2: 'FUNC', 3: 'SECTION', 4: 'FILE'}


def _read_symbol_table(g):
    def read_symbol_type(info):
        s_type = info & 0xf
        try:
            return _type_names[s_type]
        except KeyError:
            return 'OTHER'

    def read_symbol_binding(info):
        bind = info >> 4
        try:
            return _bind_names[bind]
        except KeyError:
            return 'OTHER'

    # Locate the section header of the symbol table
    sht_symtab_const = 2
    for s in g.sections:
        if s.type == sht_symtab_const:
            sh = s
            break

    # Read Each Symbol
    n_symbols = sh.size // sh.entSize
    g.symbols = []
    for i in range(n_symbols):
        # Read Symbol Table Entry
        offset = sh.offset + i * sh.entSize
        ent_content = g.content[offset:offset + 16]
        s = Symbol()
        s.name_index, s.value, s.size, s.info, s.other, s.shndex = struct.unpack(byte_order + "IIIbbH", ent_content)

        # Convert Integers to human readable strings
        s.name = _read_name(g, sh.link, s.name_index)
        s.binding = read_symbol_binding(s.info)
        s.type = read_symbol_type(s.info)

        # Save the data to a global variable
        g.symbols.append(s)

        # file = r"D:\WorstCaseStack\functions.o"
        # pprint.pprint(read_symbols(file))
