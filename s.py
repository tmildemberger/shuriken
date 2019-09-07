import os
import sys

class MetalParser:
    def __init__(self):
        self.files_to_build = list()
        self.found_libs = list()
        self.execs = list()
        self.opts = dict(c='-Wall -Wextra -Wformat-nonliteral -Wcast-align -Wpointer-arith -Wbad-function-cast -Wmissing-prototypes -Wmissing-declarations -Winline -Wundef -Wnested-externs -Wcast-qual -Wshadow -Wwrite-strings -Wfloat-equal -pedantic -std=c99'.split(' '),
                         cpp='-std=c++17 -pedantic -pedantic-errors -Wall -Wextra -g -ggdb -Wcast-align -Wcast-qual -Wctor-dtor-privacy -Wdisabled-optimization -Wformat=2 -Wmissing-declarations -Wmissing-include-dirs -Wold-style-cast -Woverloaded-virtual -Wredundant-decls -Wshadow -Wsign-conversion -Wsign-promo -Wstrict-overflow=5 -Wswitch-default -Wundef -Werror'.split(' '))

    def parse_exec(self, line_number, words):
        if len(words) < 3:
            print('syntax error at line', line_number)
            print('not enough arguments')
            return
        name = words[1].replace('.', os.path.split(os.getcwd())[1])
        selectors = words[2:words.index('using') if 'using' in words else None]
        usings = words[words.index('using') + 1:] if 'using' in words else []
        files = self._select_files(selectors)
        this = dict(name=name, files=[], libs=[])
        for l in usings:
            if l not in list(k['name'] for k in self.found_libs):
                print(f'error: requested lib {l} not found')
                return
            this['libs'].append(list(k for k in self.found_libs if k['name'] == l)[0])
        for f in files:
            o = dict(name=f, opt=self.opts.copy(), libs=this['libs'])
            if o in self.files_to_build:
                i = self.files_to_build.index(o)
                o = self.files_to_build[i]
            else:
                self.files_to_build.append(o)
            this['files'].append(o)
        self.execs.append(this)
    
    def parse(self, filename):
        # print(f'file {filename} being parsed')
        lines = self._read_sep_lines(filename)
        for line_number, line in enumerate(lines):
            words = self._sep_words(line)
            coiso = (self, f'parse_{words[0]}')
            if hasattr(*coiso):
                getattr(*coiso)(line_number, words)
            else:
                print('uninplemented')
        for n in set(f['name'] for f in self.files_to_build):
            l = len(list(o for o in self.files_to_build if o['name'] == n))
            for n, k in enumerate(list(o for o in self.files_to_build if o['name'] == n)):
                if l == 1:
                    k['extra'] = ''
                else:
                    k['extra'] = f'.{n}'
        self._gen_ninja()

    def _read_sep_lines(self, filename):
        try:
            with open(filename) as f:
                return f.read().splitlines()
        except IOError as e:
            print(f'-- Could not read file: "{filename}"', end=' ')
            print(f'(IOError {e.errno}: {e.strerror})')
            exit(1)

    def _sep_words(self, line):
        return list(filter(None, line.split(' ')))

    def _select_files(self, selectors):
        import glob
        added = set()
        removed = set()
        for sel in selectors:
            neg = False
            if sel[0] in ['!', '-']:
                sel = sel[1:]
                neg = True
            files = set(glob.iglob(sel))
            if not neg:
                added |= files
            else:
                removed |= files
        return set(map(lambda x: os.path.relpath(x, '.'), added - removed))
    
    def _gen_ninja(self):
        if sys.platform.startswith('win32'):
            obj_ext = '.obj'
            exe_ext = '.exe'
            slash = '\\'
        elif sys.platform.startswith('linux'):
            obj_ext = '.o'
            exe_ext = ''
            slash = '/'

        ninja_rules = ''
        ninja_builds = ''
        lang_rules = []
        for uh in self.files_to_build:
            filename = uh['name']
            if filename.endswith('.c') or filename.endswith('.cpp'):
                local = filename
                while local.startswith(f'..{slash}'):
                    local = local[3:]
                obj_dir = f'obj{slash}'
                uh['objname'] = obj_dir + local + uh['extra'] + obj_ext
            if filename.endswith('.c'):
                if not 'c' in lang_rules:
                    ninja_rules += 'CC = gcc\n'
                    ninja_rules += 'rule compile_c\n'
                    ninja_rules += '  command = $CC ${c_flags} -MMD -MT $out -MF $out.dep -c $in -o $out\n'
                    ninja_rules += '  description = compile(c) $out\n'
                    ninja_rules += '  depfile = $out.dep\n'
                    ninja_rules += '  deps = gcc\n\n'
                    lang_rules.append('c')
                    pass
                ninja_builds += f'build {uh["objname"]}: compile_c {filename}\n'
                ninja_builds += f'  c_flags = {" ".join(uh["opt"]["c"]).strip() + " "}\n'
                pass
            if filename.endswith('.cpp'):
                if not 'cpp' in lang_rules:
                    ninja_rules += 'CXX = g++\n'
                    ninja_rules += 'rule compile_cpp\n'
                    ninja_rules += '  command = $CXX ${cxx_flags} -MMD -MT $out -MF $out.dep -c $in -o $out\n'
                    ninja_rules += '  description = compile(cpp) $out\n'
                    ninja_rules += '  depfile = $out.dep\n'
                    ninja_rules += '  deps = gcc\n\n'
                    lang_rules.append('cpp')
                    pass
                compiler_f = set()
                if 'libs' in uh:
                    for l in uh['libs']:
                        compiler_f.add(l['compiler'])
                ninja_builds += f'build {uh["objname"]}: compile_cpp {filename}\n'
                ninja_builds += f'  cxx_flags = {" ".join(uh["opt"]["cpp"]).strip() + " "}{" ".join(compiler_f)}\n'
            pass
        for uh in self.execs:
            uh['name'] += exe_ext
            if not 'link' in lang_rules:
                ninja_rules += 'LINKER_EXE = g++\n'
                ninja_rules += 'rule link_exe\n'
                ninja_rules += '  command = $LINKER_EXE ${ld_flags} -o $out $in ${ld_libs}\n'
                ninja_rules += '  description = link(exe) $out\n\n'
                lang_rules.append('link')
                pass
            ninja_builds += f'build {uh["name"]}: link_exe {" ".join(m["objname"] for m in uh["files"])}\n'
            linker_f = set()
            linker_libs = set()
            if 'libs' in uh:
                for l in uh['libs']:
                    linker_f.add(l['linker'])
                    linker_libs.add(l['libs'])
            if linker_f:
                ninja_builds += f'  ld_flags = {" ".join(linker_f)}\n'
            if linker_libs:
                ninja_builds += f'  ld_libs = {" ".join(linker_libs)}\n'
            pass

        ninja_file = 'builddir = ninja\n'
        ninja_file += ninja_rules
        ninja_file += ninja_builds
        with open('build.ninja', 'w') as out:
            out.write(ninja_file)

    def parse_configlib(self, line_number, words):
        if len(words) == 1:
            print('syntax error at line', line_number)
            print('not enough arguments')
            return
        elif len(words) > 2:
            print('syntax error at line', line_number)
            print('too many arguments')
            return
        lib = words[1]
        if self.found_configs.get(lib, False) == False:
            print('error at line', line_number)
            print("couldn't find the wanted library")
            return
        c, lk, lb = self.parse_config(self.found_configs[lib])
        klib = dict(name=lib, compiler=c, linker=lk, libs=lb)
        self.found_libs.append(klib)
        return
        pass

    def parse_disable(self, line_number, words):
        if len(words) < 3:
            print('syntax error at line', line_number)
            print('not enough arguments')
            return
        if words[1] not in ['c', 'cpp']:
            print('error at line', line_number)
            print(words[1], 'is not c nor cpp')
            return
        language = words[1]
        options = words[2:]
        for op in options:
            if op in self.opt[language]:
                self.opt[language].remove(op)
                pass
            pass
        pass
    
    def parse_lines(self, content):
        idx = 0
        # possible_tokens = ['info', 'path', 'compiler', 'linker', 'libs']
        path = ''
        compiler_flags = ''
        linker_flags = ''
        linker_libs = ''
        if not content.endswith('\n'):
            content = content + '\n'
        # print(len(content), content)
        while idx < len(content): # and content.startswith(possible_tokens, idx):
            # print(idx, content[idx:idx+4], content.startswith('info', idx), path)
            if content.startswith('info', idx):
                while content[idx] != '"':
                    idx += 1
                idx += 1
                while content[idx] != '"':
                    idx += 1
                while content[idx] != '\n':
                    idx += 1
                idx += 1
            elif content.startswith('path', idx):
                path = (content[idx:].split(None, 1))[1].split('\n', 1)[0]
                while content[idx] != '\n':
                    idx += 1
                idx += 1
            elif content.startswith('compiler', idx):
                compiler_flags = (content[idx:].split(None, 1))[1].split('\n', 1)[0] + '  '
                place = compiler_flags.find('$path$')
                while place != -1:
                    compiler_flags = compiler_flags[:place] + path + compiler_flags[place+6:]
                    place = compiler_flags.find('$path$')

                while content[idx] != '\n':
                    idx += 1
                idx += 1
            elif content.startswith('linker', idx):
                linker_flags = (content[idx:].split(None, 1))[1].split('\n', 1)[0] + '  '
                place = linker_flags.find('$path$')
                # print('linkerflags', linker_flags)
                # print('place', place)
                # print('path', path)
                # linker_flags = linker_flags[:place] + path + linker_flags[place+6:]
                # place = linker_flags.find('$path$')
                # print('linkerflags', linker_flags)
                # print('place', place)
                while place != -1:
                    linker_flags = linker_flags[:place] + path + linker_flags[place+6:]
                    place = linker_flags.find('$path$')

                while content[idx] != '\n':
                    idx += 1
                idx += 1
            elif content.startswith('libs', idx):
                linker_libs = (content[idx:].split(None, 1))[1].split('\n', 1)[0] + '  '
                place = linker_libs.find('$path$')
                while place != -1:
                    linker_libs = linker_libs[:place] + path + linker_libs[place+6:]
                    place = linker_libs.find('$path$')

                while content[idx] != '\n':
                    idx += 1
                idx += 1
            else:
                idx += 1
            pass
        pass
        compiler_flags = compiler_flags.strip()
        linker_flags = linker_flags.strip()
        linker_libs = linker_libs.strip()
        return compiler_flags, linker_flags, linker_libs

    def parse_config(self, file):
        with open(file, "r") as config:
            content = config.read()
            flags = self.parse_lines(content)
            return flags
            pass
        pass

    def set_found_configs(self):
        config_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config')
        os.makedirs(config_folder, exist_ok=True)
        files = {}
        for fl in os.listdir(config_folder):
            if fl.endswith('.cfg'):
                files[fl[:-4]] = os.path.join(config_folder, fl)
        self.found_configs = files.copy()
        return

if __name__ == '__main__':
    # executed as a script
    
    if os.path.isfile('metal'):
        parser = MetalParser()
        parser.set_found_configs()
        parser.parse('metal')
    else:
        print('no metal file found')