class MetalParser:
    def parse_exec(self):
        return 'parsed'
    
    def parse(self, filename):
        print(f'file {filename} parsed')
        lines = self._read_sep_lines(filename)
        for line in lines:
            words = self._sep_words(line)
            print(words)

    def _read_sep_lines(self, filename):
        try:
            with open(filename) as f:
                return f.read().splitlines()
                # yield f.readline()
                # return list(f)
        except IOError as e:
            print(f'-- Could not read file: "{filename}"', end=' ')
            print(f'(IOError {e.errno}: {e.strerror})')
            exit(1)
            # "I/O error({0}): {1}".format(e.errno, e.strerror)
        # f = open(filename)
        # ret = list(f)
        # f.close()
        # return ret
    def _sep_words(self, line):
        return list(filter(None, line.split(' ')))

parser = MetalParser()
parser.parse('metal')