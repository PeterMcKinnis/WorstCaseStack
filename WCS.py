# pylint: disable = invalid-name, too-few-public-methods

import re
import pprint
import os
import sys
from typing import List, Tuple, Dict, Any
from subprocess import check_output

# Constants
rtl_ext_end = ".dfinish"
su_ext = '.su'
obj_ext = '.o'
manual_ext = '.msu'
read_elf_path = os.getenv("CROSS_COMPILE", "") + "readelf"
stdout_encoding = "utf-8"  # System dependant


class Printable:
    def __repr__(self) -> str:
        return "<" + type(self).__name__ + "> " + pprint.pformat(vars(self), indent=4, width=1)


class Symbol(Printable):
    # value: int = -1
    # size: int = -1
    type: str = "uninitialized"
    binding: str = "uninitialized"
    name: str = "uninitialized"


CallNode = Dict[str, Any]


def calc_wcs(fxn_dict2: CallNode, parents: List[CallNode]) -> None:
    """
    Calculates the worst case stack for a fxn that is declared (or called from) in a given file.
    :param parents: This function gets called recursively through the call graph.  If a function has recursion the
    tuple file, fxn will be in the parents stack and everything between the top of the stack and the matching entry
    has recursion.
    :return:
    """

    # If the wcs is already known, then nothing to do
    if 'wcs' in fxn_dict2:
        return

    # Check for pointer calls
    if fxn_dict2['has_ptr_call']:
        fxn_dict2['wcs'] = 'unbounded'
        return

    # Check for recursion
    if fxn_dict2 in parents:
        fxn_dict2['wcs'] = 'unbounded'
        return

    # Calculate WCS
    call_max = 0
    for call_dict in fxn_dict2['r_calls']:

        # Calculate the WCS for the called function
        calc_wcs(call_dict, parents + [fxn_dict2])

        # If the called function is unbounded, so is this function
        if call_dict['wcs'] == 'unbounded':
            fxn_dict2['wcs'] = 'unbounded'
            return

        # Keep track of the call with the largest stack use
        call_max = max(call_max, call_dict['wcs'])

        # Propagate Unresolved Calls
        for unresolved_call in call_dict['unresolved_calls']:
            fxn_dict2['unresolved_calls'].add(unresolved_call)

    fxn_dict2['wcs'] = call_max + fxn_dict2['local_stack']


class CallGraph:
    globals: Dict[str, CallNode] = {}
    locals: Dict[str, Dict[str, CallNode]] = {}
    weak: Dict[str, CallNode] = {}

    def read_obj(self, tu: str) -> None:
        """
        Reads the file tu.o and gets the binding (global or local) for each function
        :param self: a object used to store information about each function, results go here
        :param tu: name of the translation unit (e.g. for main.c, this would be 'main')
        """

        for s in read_symbols(tu[0:tu.rindex(".")] + obj_ext):

            if s.type == 'FUNC':
                if s.binding == 'GLOBAL':
                    # Check for multiple declarations
                    if s.name in self.globals or s.name in self.locals:
                        raise Exception(f'Multiple declarations of {s.name}')
                    self.globals[s.name] = {'tu': tu, 'name': s.name, 'binding': s.binding}
                elif s.binding == 'LOCAL':
                    # Check for multiple declarations
                    if s.name in self.locals and tu in self.locals[s.name]:
                        raise Exception(f'Multiple declarations of {s.name}')

                    if s.name not in self.locals:
                        self.locals[s.name] = {}

                    self.locals[s.name][tu] = {'tu': tu, 'name': s.name, 'binding': s.binding}
                elif s.binding == 'WEAK':
                    if s.name in self.weak:
                        raise Exception(f'Multiple declarations of {s.name}')
                    self.weak[s.name] = {'tu': tu, 'name': s.name, 'binding': s.binding}
                else:
                    raise Exception(f'Error Unknown Binding "{s.binding}" for symbol: {s.name}')

    def find_fxn(self, tu: str, fxn: str):
        """
        Looks up the dictionary associated with the function.
        :param self: a object used to store information about each function
        :param tu: The translation unit in which to look for locals functions
        :param fxn: The function name
        :return: the dictionary for the given function or None
        """

        if fxn in self.globals:
            return self.globals[fxn]
        try:
            return self.locals[fxn][tu]
        except KeyError:
            return None

    def find_demangled_fxn(self, tu: str, fxn: str):
        """
        Looks up the dictionary associated with the function.
        :param self: a object used to store information about each function
        :param tu: The translation unit in which to look for locals functions
        :param fxn: The function name
        :return: the dictionary for the given function or None
        """
        for f in self.globals.values():
            if 'demangledName' in f:
                if f['demangledName'] == fxn:
                    return f
        for f in self.locals.values():
            if tu in f:
                if 'demangledName' in f[tu]:
                    if f[tu]['demangledName'] == fxn:
                        return f[tu]
        return None

    def read_rtl(self, tu: str, rtl_ext: str) -> None:
        """
        Read an RTL file and finds callees for each function and if there are calls via function pointer.
        :param self: a object used to store information about each function, results go here
        :param tu: the translation unit
        """

        # Construct A Call Graph
        function = re.compile(r'^;; Function (.*) \((\S+), funcdef_no=\d+(, [a-z_]+=\d+)*\)( \([a-z ]+\))?$')
        static_call = re.compile(r'^.*\(call.*"(.*)".*$')
        other_call = re.compile(r'^.*call .*$')

        with open(tu + rtl_ext, "rt", encoding="latin_1") as file_:
            for line_ in file_:
                m = function.match(line_)
                if m:
                    fxn_name = m.group(2)
                    fxn_dict2 = self.find_fxn(tu, fxn_name)
                    if not fxn_dict2:
                        pprint.pprint(self)
                        raise Exception(f"Error locating function {fxn_name} in {tu}")

                    fxn_dict2['demangledName'] = m.group(1)
                    fxn_dict2['calls'] = set()
                    fxn_dict2['has_ptr_call'] = False
                    continue

                m = static_call.match(line_)
                if m:
                    fxn_dict2['calls'].add(m.group(1))
                    # print("Call:  {0} -> {1}".format(current_fxn, m.group(1)))
                    continue

                m = other_call.match(line_)
                if m:
                    fxn_dict2['has_ptr_call'] = True
                    continue

    def read_su(self, tu: str) -> None:
        """
        Reads the 'local_stack' for each function.  Local stack ignores stack used by callees.
        :param self: a object used to store information about each function, results go here
        :param tu: the translation unit
        :return:
        """
    # Needs to be able to handle both cases, i.e.:
    #   c:\\userlibs\\gcc\\arm-none-eabi\\include\\assert.h:41:6:__assert_func	16	static
    #   main.c:113:6:vAssertCalled	8	static
    # Now Matches six groups https://regex101.com/r/Imi0sq/1

        su_line = re.compile(r'^(.+):(\d+):(\d+):(.+)\t(\d+)\t(\S+)$')
        i = 1

        with open(tu[0:tu.rindex(".")] + su_ext, "rt", encoding="latin_1") as file_:
            for line in file_:
                m = su_line.match(line)
                if m:
                    fxn = m.group(4)
                    fxn_dict2 = self.find_demangled_fxn(tu, fxn)
                    fxn_dict2['local_stack'] = int(m.group(5))
                else:
                    print(f"error parsing line {i} in file {tu}")
                i += 1

    def read_manual(self, file: str) -> None:
        """
        reads the manual stack useage files.
        :param self: a object used to store information about each function, results go here
        :param file: the file name
        """

        with open(file, "rt", encoding="latin_1") as file_:
            for line in file_:
                fxn, stack_sz = line.split()
                if fxn in self.globals:
                    raise Exception(f"Redeclared Function {fxn}")
                self.globals[fxn] = {'wcs': int(stack_sz),
                                     'calls': set(),
                                     'has_ptr_call': False,
                                     'local_stack': int(stack_sz),
                                     'is_manual': True,
                                     'name': fxn,
                                     'demangledName': fxn,
                                     'tu': '#MANUAL',
                                     'binding': 'GLOBAL'}

    def validate_all_data(self) -> None:
        """
        Check that every entry in the call graph has the following fields:
        .calls, .has_ptr_call, .local_stack, .scope, .src_line
        """

        def validate_dict(d):
            if not ('calls' in d and 'has_ptr_call' in d and 'local_stack' in d
                    and 'name' in d and 'tu' in d):
                print(f"Error data is missing in fxn dictionary {d}")

        # Loop through every global and local function
        # and resolve each call, save results in r_calls
        for fxn_dict2 in self.globals.values():
            validate_dict(fxn_dict2)

        for l_dict in self.locals.values():
            for fxn_dict2 in l_dict.values():
                validate_dict(fxn_dict2)

    def resolve_all_calls(self) -> None:
        def resolve_calls(fxn_dict2: CallNode) -> None:
            fxn_dict2['r_calls'] = []
            fxn_dict2['unresolved_calls'] = set()

            for call in fxn_dict2['calls']:
                call_dict = self.find_fxn(fxn_dict2['tu'], call)
                if call_dict:
                    fxn_dict2['r_calls'].append(call_dict)
                else:
                    fxn_dict2['unresolved_calls'].add(call)

        # Loop through every global and local function
        # and resolve each call, save results in r_calls
        for fxn_dict in self.globals.values():
            resolve_calls(fxn_dict)

        for l_dict in self.locals.values():
            for fxn_dict in l_dict.values():
                resolve_calls(fxn_dict)

    def calc_all_wcs(self) -> None:
        # Loop through every global and local function
        # and resolve each call, save results in r_calls
        for fxn_dict in self.globals.values():
            calc_wcs(fxn_dict, [])

        for l_dict in self.locals.values():
            for fxn_dict in l_dict.values():
                calc_wcs(fxn_dict, [])

    def print_all_fxns(self) -> None:

        def print_fxn(row_format: str, fxn_dict2: CallNode) -> None:
            unresolved = fxn_dict2['unresolved_calls']
            stack = str(fxn_dict2['wcs'])
            if unresolved:
                unresolved_str = f"({' ,'.join(unresolved)})"
                if stack != 'unbounded':
                    stack = "unbounded:" + stack
            else:
                unresolved_str = ''

            print(row_format.format(fxn_dict2['tu'], fxn_dict2['demangledName'], stack, unresolved_str))

        def get_order(val) -> int:
            return 1 if val == 'unbounded' else -val

        # Loop through every global and local function
        # and resolve each call, save results in r_calls
        d_list = []
        for fxn_dict in self.globals.values():
            d_list.append(fxn_dict)

        for l_dict in self.locals.values():
            for fxn_dict in l_dict.values():
                d_list.append(fxn_dict)

        d_list.sort(key=lambda item: get_order(item['wcs']))

        # Calculate table width
        tu_width = max(max(len(d['tu']) for d in d_list), 16)
        name_width = max(max(len(d['name']) for d in d_list), 13)
        row_format = "{:<" + str(tu_width + 2) + "}  {:<" + str(name_width + 2) + "}  {:>14}  {:<17}"

        # Print out the table
        print("")
        print(row_format.format('Translation Unit', 'Function Name', 'Stack', 'Unresolved Dependencies'))
        for d in d_list:
            print_fxn(row_format, d)


def read_symbols(file: str) -> List[Symbol]:

    def to_symbol(read_elf_line: str) -> Symbol:
        v = read_elf_line.split()

        s2 = Symbol()
        # s2.value = int(v[1], 16)
        # if ('x' in v[2]):
        #     #raise Exception(f'Mixed symbol sizes in \'{v}\' ')
        #     s2.size=int(v[2].split('x')[1],16)
        # else:
        #     s2.size = int(v[2])
        s2.type = v[3]
        s2.binding = v[4]
        s2.name = v[7] if len(v) >= 8 else ""

        return s2
    output = check_output([read_elf_path, "-s", "-W", file]).decode(stdout_encoding)
    lines = output.splitlines()[3:]
    return [to_symbol(line) for line in lines]


def find_rtl_ext() -> str:
    # Find the rtl_extension

    for _, _, filenames in os.walk('.'):
        for f in filenames:
            if f.endswith(rtl_ext_end):
                rtl_ext = f[f[:-len(rtl_ext_end)].rindex("."):]
                print("rtl_ext = " + rtl_ext)
                return rtl_ext

    print("Could not find any files ending with '.dfinish'.  Check that the script is being run from the correct "
          "directory.  Check that the code was compiled with the correct flags")
    sys.exit(-1)


def find_files(rtl_ext: str) -> Tuple[List[str], List[str]]:
    tu: List[str] = []
    manual: List[str] = []
    all_files: List[str] = []
    for root, _, filenames in os.walk('.'):
        for filename in filenames:
            all_files.append(os.path.join(root, filename))
    for f in [f for f in all_files if os.path.isfile(f) and f.endswith(rtl_ext)]:
        base = f[0:-len(rtl_ext)]
        short_base = base[0:base.rindex(".")]
        if short_base + su_ext in all_files and short_base + obj_ext in all_files:
            tu.append(base)
            print(f'Reading: {base}{rtl_ext}, {short_base}{su_ext}, {short_base}{obj_ext}')

    for f in [f for f in all_files if os.path.isfile(f) and f.endswith(manual_ext)]:
        manual.append(f)
        print(f'Reading: {f}')

    # Print some diagnostic messages
    if not tu:
        print("Could not find any translation units to analyse")
        sys.exit(-1)

    return tu, manual


def main() -> None:
    # Find the appropriate RTL extension
    rtl_ext = find_rtl_ext()

    # Find all input files
    call_graph: CallGraph = CallGraph()
    tu_list, manual_list = find_files(rtl_ext)

    # Read the input files
    for tu in tu_list:
        call_graph.read_obj(tu)  # This must be first

    for fxn in call_graph.weak.values():
        if fxn['name'] not in call_graph.globals:
            call_graph.globals[fxn['name']] = fxn

    for tu in tu_list:
        call_graph.read_rtl(tu, rtl_ext)
    for tu in tu_list:
        call_graph.read_su(tu)

    # Read manual files
    for m in manual_list:
        call_graph.read_manual(m)

    # Validate Data
    call_graph.validate_all_data()

    # Resolve All Function Calls
    call_graph.resolve_all_calls()

    # Calculate Worst Case Stack For Each Function
    call_graph.calc_all_wcs()

    # Print A Nice Message With Each Function and the WCS
    call_graph.print_all_fxns()


main()
