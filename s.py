import os
import sys

class MetalParser:
    def __init__(self):
        self.files_to_build = list()
        self.execs = list()
        self.opts = dict(c='-Wall -Wextra -Wformat-nonliteral -Wcast-align -Wpointer-arith -Wbad-function-cast -Wmissing-prototypes -Wmissing-declarations -Winline -Wundef -Wnested-externs -Wcast-qual -Wshadow -Wwrite-strings -Wfloat-equal -pedantic -std=c99'.split(' '),
                         cpp='-std=c++17 -pedantic -pedantic-errors -Wall -Wextra -g -ggdb -Wcast-align -Wcast-qual -Wctor-dtor-privacy -Wdisabled-optimization -Wformat=2 -Wmissing-declarations -Wmissing-include-dirs -Wold-style-cast -Woverloaded-virtual -Wredundant-decls -Wshadow -Wsign-conversion -Wsign-promo -Wstrict-overflow=5 -Wswitch-default -Wundef -Werror'.split(' '))
        self.defines = list()
        self.defines.append(('.', os.path.split(os.getcwd())[1]))

    def parse_def(self, line_number, words):
        if len(words) < 2:
            print('syntax error at line', line_number)
            print('not enough arguments')
            return
        name = words[1]
        words.append('')
        self.defines.append((name, ' '.join(words[2:]).strip()))

    def parse_undef(self, line_number, words):
        if len(words) < 2:
            print('syntax error at line', line_number)
            print('not enough arguments')
            return
        deletes = []
        for df in words[1:]:
            for i, a in enumerate(self.defines):
                if a[0] == df:
                    deletes.append(i)
        for i in deletes:
            del self.defines[i]

    def parse_exec(self, line_number, words):
        if len(words) < 3:
            print('syntax error at line', line_number)
            print('not enough arguments')
            return
        name = words[1]
        print(self.defines)
        for df in self.defines:
            name = name.replace(*df)
        print()
        # name = words[1].replace('.', os.path.split(os.getcwd())[1])
        selectors = words[2:words.index('using') if 'using' in words else None]
        files = self._select_files(selectors)
        this = dict(name=name, files=[])
        for f in files:
            o = dict(name=f, opt=self.opts.copy())
            if o in self.files_to_build:
                i = self.files_to_build.index(o)
                o = self.files_to_build[i]
            else:
                self.files_to_build.append(o)
            this['files'].append(o)
        self.execs.append(this)
    
    def parse(self, filename):
        print(f'file {filename} being parsed')
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
            print(filename)
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
                ninja_builds += f'build {uh["objname"]}: compile_cpp {filename}\n'
                ninja_builds += f'  cxx_flags = {" ".join(uh["opt"]["cpp"]).strip() + " "}\n'
                pass
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
            # if pack['linker_f'] != '':
            #     ninja_builds += '  ld_flags = {0}\n'.format(pack['linker_f'])
            # if pack['linker_libs'] != '':
            #     ninja_builds += '  ld_libs = {0}\n'.format(pack['linker_libs'])
            pass

        ninja_file = 'builddir = ninja\n'
        ninja_file += ninja_rules
        ninja_file += ninja_builds
        with open('build.ninja', 'w') as out:
            out.write(ninja_file)

if __name__ == '__main__':
    # executed as a script
    
    if os.path.isfile('metal'):
        parser = MetalParser()
        parser.parse('metal')
    else:
        print('no metal file found')