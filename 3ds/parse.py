'''
    Description: This is the 3DS file parser, it produces a 3ds file object
        with the File3Ds.open method
    Status: Nearly complete, some bone data missing
    License: AGPLv3, see LICENSE for more details
    Copyright: 2011 Florian Boesch <pyalot@gmail.com>
    Helpful Links:
        http://en.wikipedia.org/wiki/.3ds
        http://www.spacesimulator.net/wiki/index.php?title=Tutorials:3ds_Loader
        http://www.martinreddy.net/gfx/3d/3DS.spec
        http://faydoc.tripod.com/formats/3ds.htm
'''
from struct import unpack
from vector import Vec2, Vec3

class Data:
    size = 0
    def __init__(self, parent, data):
        self.parent = parent
    def __repr__(self):
        return self.__class__.__name__

class Main(Data): pass
class Editor(Data): pass
class Object(Data):
    def __init__(self, parent, data):
        self.parent = parent
        zero_index = data.find('\0')
        self.name = data[:zero_index]
        self.size = zero_index+1

    def __repr__(self):
        return '%s %s' % (self.__class__.__name__, self.name)

class Mesh(Data): pass

class Vertices(Data):
    def __init__(self, parent, data):
        self.parent = parent
        count = unpack('H', data[:2])[0]
        data = data[2:]
        self.vertices = []
        for i in range(count):
            x, y, z = unpack('fff', data[:3*4])
            data = data[3*4:]
            self.vertices.append(Vec3(x,z,-y))
        self.size = 2 + count*3*4

        for i, v1 in enumerate(self.vertices):
            for j, v2 in list(enumerate(self.vertices))[i+1:]:
                if v1.x == v2.x and v1.y == v2.y and v1.z == v2.z:
                    self.vertices[j] = v1

class Faces(Data):
    def __init__(self, parent, data):
        self.parent = parent
        count = unpack('H', data[:2])[0]
        data = data[2:]
        self.faces = []
        for i in range(count):
            j = i+1
            v1, v2, v3, flags = unpack('HHHH', data[i*4*2:j*4*2])
            self.faces.append((v1, v2, v3, flags))
        self.size = 2 + count*4*2

class FaceMaterial:
    def __init__(self, parent, data):
        self.parent = parent
        zero_index = data.find('\0')
        self.name = data[:zero_index]
        data = data[zero_index+1:]

        count = unpack('H', data[:2])[0]
        data = data[2:]
        #todo get indices
        self.faces = []
        for i in range(count):
            face_index = unpack('H', data[:2])[0]
            data = data[2:]
            self.faces.append(face_index)
        self.size = zero_index+1 + 2 + count*2
    
    def __repr__(self):
        return '%s %s' % (self.__class__.__name__, self.name)

class Texcoords(Data):
    def __init__(self, parent, data):
        self.parent = parent
        count = unpack('H', data[:2])[0]
        data = data[2:]
        self.texcoords = []
        for i in range(count):
            x, y = unpack('ff', data[:8])
            data = data[8:]
            self.texcoords.append(Vec2(x,1.0-y))
        self.size = 2 + count*2*4

class Matrix(Data):
    def __init__(self, parent, data):
        self.parent = parent
        self.size = 12*4
        r11, r21, r31, r21, r22, r23, r31, r32, r33, x, y, z = unpack('f'*12, data)
        self.rot = [r11, r21, r31, r21, r22, r23, r31, r32, r33]
        self.center = Vec3(x, z, -y)

class SmoothGroup(Data):
    def __init__(self, parent, data):
        self.size = len(data)
        self.parent = parent
        self.groups = []
        for i in range(len(parent.parent.data.faces)):
            group_id = unpack('i', data[:4])[0]
            self.groups.append(group_id)
            data = data[4:]

class Keyframer(Data): pass
class ObjectDescription(Data): pass

class ObjectHirarchy(Data):
    def __init__(self, parent, data):
        self.parent = parent
        self.parent = parent
        zero_index = data.find('\0')
        self.name = data[:zero_index]
        data = data[zero_index+1:]
        self.size = zero_index+1 + 3*4
        self.hirarchy = unpack('H', data[4:6])[0]
    
    def __repr__(self):
        return '%s %s %i' % (self.__class__.__name__, self.name, self.hirarchy)

names = {
    0x4d4d: Main, 
    0x3d3d: Editor,
    0x4000: Object,
    0x4100: Mesh,
    0x4110: Vertices,
    0x4120: Faces,
    0x4140: Texcoords,
    0x4160: Matrix,
    0x4130: FaceMaterial,
    0x4150: SmoothGroup,
    0xb000: Keyframer,
    0xb002: ObjectDescription,
    0xb010: ObjectHirarchy,
}

def print_chunk(chunk, indent=0):
    print '%s%04X: %s' % ('  '*indent, chunk.id, chunk.name)
    for child in chunk.children:
        print_chunk(child, indent+1)

class Children(object):
    def __init__(self):
        self.list = []
        self.map = {}

    def add(self, child):
        name = child.name.lower()
        map = self.map
        self.list.append(child)
        if name in map:
            if isinstance(map[name], list):
                map[name].append(child)
            else:
                map[name] = [map[name], child]
        else:
            map[name] = child

    def __iter__(self):
        return iter(self.list)

    def __getitem__(self, key):
        if isinstance(key, str):
            return self.map[key]
        else:
            return self.list[key]

    def __getattr__(self, name):
        return self.map[name]

class Chunk:
    def __init__(self, parent, id, data):
        self.parent = parent
        self.id = id
        self.name = 'unknown'
        self.data = None
        self.children = Children()
        if id in names:
            self.data = names[id](self, data)
            #self.name = '%s' % self.data
            self.name = self.data.__class__.__name__
            self.parse_chunks(data[self.data.size:])

    def parse_chunks(self, data):
        while data:
            id = unpack('H', data[:2])[0]
            length = unpack('i', data[2:6])[0]
            self.children.add(Chunk(self, id, data[6:length]))
            data = data[length:]

class File3Ds:
    @staticmethod
    def open(filename):
        data = open(filename, 'rb').read()
        return File3Ds(data)

    def __init__(self, data):
        self.data = data
        id = unpack('H', data[:2])[0]
        length = unpack('i', data[2:6])[0]
        data = data[6:]
        self.main = Chunk(self, id, data)

if __name__ == '__main__':
    import sys
    filename = sys.argv[1]
    infile = File3Ds.open(filename)
    for obj in infile.main.children.editor.children.object:
        mesh = obj.children.mesh
        faces = mesh.children.faces
        vertices = mesh.children.vertices
        texcoords = mesh.children.texcoords
        center = mesh.children.matrix.data.center
        groups = faces.children.smoothgroup.data.groups
        for i, (v1, v2, v3, flags) in enumerate(faces.data.faces):
            group = groups[i]
            vert1 = vertices.data.vertices[v1]
            vert2 = vertices.data.vertices[v2]
            vert3 = vertices.data.vertices[v3]
            uv1 = texcoords.data.texcoords[v1]
            uv2 = texcoords.data.texcoords[v2]
            uv3 = texcoords.data.texcoords[v3]


    print_chunk(infile.main)
