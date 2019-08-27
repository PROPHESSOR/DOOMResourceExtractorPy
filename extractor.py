#!/usr/bin/python3
# coding: utf-8

import os
import json
import zlib

FILE = "base/gameresources"

VERBOSE = False

class ByteTools():
    def __init__(self, stream):
        self.stream = stream
        self.order = 'little'

    def byteorder(self, order=None):
        if not order:
            return self.order

        self.order = order

    def parseASCIIString(self, length):
        return self.stream.read(length).decode('ascii')

    def parseUnicodeString(self, length):
        return self.stream.read(length).decode('utf-8')

    def parseString(self, length): return self.parseUnicodeString(length)

    def parseUInt(self, x):
        return int.from_bytes(self.stream.read(x), byteorder=self.order, signed=False)

    def parseUInt8(self):  return self.parseUInt(1)
    def parseUInt16(self): return self.parseUInt(2)
    def parseUInt32(self): return self.parseUInt(4)

    def parseInt(self, x):
        return int.from_bytes(self.stream.read(x), byteorder=self.order, signed=True)

    def parseInt8(self):  return self.parseInt(1)
    def parseInt16(self): return self.parseInt(2)
    def parseInt32(self): return self.parseInt(4)
    def parseInt64(self): return self.parseInt(8)

print("File: %s" % FILE + '.index')

print("Generating file list...")

with open(FILE + '.index', 'rb') as _in:
    index = ByteTools(_in)

    magic = index.parseInt32()

    if (magic & 0xFFFFFF00) != 0x52455300:
        print("Not an .index file! (Magic number error)")
        exit()

    header_version = magic & 0xFF

    print("Header version: %d" % header_version)

    header_indexsize = index.parseInt32()

    if VERBOSE: print("Header indexsize: %d" % header_indexsize)

    print("Opening %s..." % FILE + '.resources')

    index.stream.seek(0x20, 0)
    index.byteorder('big')

    header_numentries = index.parseInt32()

    print("Found %d files!" % header_numentries)

    entries = []

    for i in range(header_numentries):
        index.byteorder('big')
        ID = index.parseInt32()

        index.byteorder('little')

        size = index.parseInt32()
        filetype = index.parseString(size)

        size = index.parseInt32()
        respath = index.parseString(size)

        size = index.parseInt32()
        filepath = index.parseString(size)

        index.byteorder('big')

        offset = index.parseInt64()

        size = index.parseInt32()

        compressedsize = index.parseInt32()

        if header_version <= 4:
            zero = index.parseInt64()
        else:
            zero = index.parseInt32()
        
        #if zero != 0:
        #    print("\tWarning! Zero assertion fault at resorce %d!" % (i + 1))

        patchfilenumber = index.parseInt8()

        if VERBOSE:
            print("#%d" % (i + 1))
            print("\tID: %d" % ID)
            print("\tType: %s" % filetype)
            print("\tResource: %s" % respath)
            print("\tPath: %s" % filepath)
            print("\tOffset: 0x%x" % offset)
            print("\tSize: %d" % size)
            print("\tCompressed size: %d" % compressedsize)
            print("\tPatch file number: %d" % patchfilenumber)

        entries.append({
            'id': ID,
            'type': filetype,
            'res': respath,
            'path': filepath,
            'offset': offset,
            'size': size,
            'comp_size': compressedsize,
            'patch': patchfilenumber
        })

def extract(pos, size, compressed=True):
    import zlib

    with open(FILE + '.resources', 'rb') as _in:
        _in.seek(pos)

        data = _in.read(size)

        if compressed:
            try:
                data = zlib.decompress(data)
            except Exception as e:
                print(e)

    return data

def generateTree(entries):
    tree = {}

    for entry in entries:
        path = entry['res']
        tokens = path.split('/')
        pure_path = path.split('$')[0]
        flags = path.split('$')[1:]
        
        if not len(tokens): return

        context = tree

        for (idx, token) in enumerate(tokens):
            if idx == (len(tokens) - 1):
                _token = token.split('$')[0] # remove flags
                context[_token] = entry
                context[_token]['pure_res'] = pure_path
                if len(flags):
                    context[_token]['flags'] = flags

            if not token in context: context[token] = {}

            context = context[token]

    return tree

def generateJSON(tree):
    with open(FILE + '.index.json', 'w') as _out:
        json.dump(tree, _out, sort_keys=True, indent=4)

class GUI:
    def __init__(self):
        import tkinter as _
        from tkinter import ttk

        self.win = _.Tk()
        self.win.title("DOOM (2016) Resource Extractor (Copyright (c) PROPHESSOR 2019)")
        self.win.attributes('-zoomed', True)
        self.tree = ttk.Treeview(self.win)
        self.tree['columns'] = ('type', 'size', 'csize')
        self.tree.column("size", width=64)
        self.tree.column("csize", width=64)
        self.tree.heading("#0", text="Name")
        self.tree.heading("type", text="Type")
        self.tree.heading("size", text="Size")
        self.tree.heading("csize", text="Compressed")
        self.tree.pack(side=_.TOP, fill=_.BOTH, expand=True)

        self._root_files = self.tree.insert("", "end", "", text="{root_files}", values=("DOOM Resource Extractor pseudo-folder", "", ""))

        self.tree.bind("<Double-1>", self.onDoubleClick)

    def alert(self, text, title="Message"):
        from tkinter import messagebox

        messagebox.showinfo(title, text)

    def confirm(self, text, title="Message"):
        from tkinter import messagebox

        return messagebox.askokcancel(title, text)

    def mainloop(self):
        self.win.mainloop()

    def toReadableSize(self, byte):
        names = ('Bytes', 'Kb', 'Mb', 'Gb')

        for name in names:
            if byte < 1: return "%s %s" % (str(round(byte, 2)), name)

            byte /= 1024

        return "%s %s" % (str(round(byte, 2)), names[-1])

    def buildTable(self, level, folder=""):
        for key in sorted(level.keys()):
            value = level[key]
            if 'id' in value: # File
                if not 'type' in value:
                    print("FIXME: [BUGGED VALUE]", value)
                    continue

                _folder = self.tree.insert(folder or self._root_files, "end", json.dumps(value), text=key, values=(value['type'], self.toReadableSize(value['size']), self.toReadableSize(value['comp_size']), json.dumps(value)))
            else: # Folderself.tree
                _folder = self.tree.insert(folder, "end", "", text=key, values=("Folder", str(len(value.keys())) + " files", ""))
                self.buildTable(value, _folder)

    def onDoubleClick(self, event):
        selection = self.tree.selection()[0]

        values = self.tree.item(selection, 'values')

        if len(values) == 4:
            data = json.loads(values[3])

            print("Double clicked on file %s" % data['pure_res'])

            compressed = data['size'] != data['comp_size']

            if self.confirm("Do you wish to extract %s? (~%s Kb) [%s]" % (data['pure_res'], str(round(data['size'] / 1024, 2)), 'COMPRESSED' if compressed else 'UNCOMPRESSED')):
                #self.alert("Extracting %s..." % data['pure_res'])
                extracted = extract(data['offset'], data['comp_size'], compressed=compressed)
                folders = '/'.join(data['pure_res'].split('/')[:-1])
                filename = data['pure_res'].split('/')[-1]
                folderpath = os.path.join(FILE, folders)
                print("Creating folders %s..." % folderpath)
                os.makedirs(folderpath)

                with open(os.path.join(folderpath, filename), 'wb') as _out:
                        _out.write(extracted)

                self.alert("Extracted successfully!")
        else:
            print("Double clicked on folder")

print("Generating file list... [OK!]")
print("Generating folder tree...")
tree = generateTree(entries)

print("Generating folder tree... [OK!]")
print("Generating JSON file...") 
generateJSON(tree)

print("Generating JSON file... [OK!]") 
print("Starting GUI...")
gui = GUI()
gui.buildTable(tree)
gui.mainloop()
