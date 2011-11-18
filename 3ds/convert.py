'''
    Description: Converts a File3Ds to json and does a bunch of other calculations (normals, tangents, scaling etc.)
    License: AGPLv3, see LICENSE for more details
    Copyright: 2011 Florian Boesch <pyalot@gmail.com>
'''

from parse import File3Ds
from vector import Vec3
import json
from random import random
from math import log

scale = 0.0005
    
class Vertex:
    def __init__(self, index, pos, uv):
        self.index = index
        self.pos = pos
        self.uv = uv

class Face:
    def __init__(self, group, v1, v2, v3):
        self.group = group
        self.v1 = v1
        self.v2 = v2
        self.v3 = v3

        edge1 = self.v2.pos - self.v1.pos
        edge2 = self.v3.pos - self.v1.pos

        edgeuv1 = self.v2.uv - self.v1.uv
        edgeuv2 = self.v3.uv - self.v2.uv
        
        self.normal = edge1.cross(edge2).normalize()

        cp = edgeuv1.y*edgeuv2.x - edgeuv1.x*edgeuv2.y
        if cp != 0:
            self.tangent   = ((edge1 * -edgeuv2.y + edge2 * edgeuv1.y) / cp).normalize();
            self.bitangent = ((edge1 * -edgeuv2.x + edge2 * edgeuv1.x) / cp).normalize();
        else:
            self.tangent = self.normal.cross(Vec3(0.00001, 0.00001, 1.0)).normalize()
            self.bitangent = self.normal.cross(self.tangent).normalize()

    def __contains__(self, vertex):
        pos = vertex.pos
        return self.v1.pos == pos or self.v2.pos == pos or self.v3.pos == pos

class Object:
    def __init__(self, index, name, center, faces):
        self.parent = None
        self.children = []
        self.index = index
        self.name = name
        self.center = center
        self.faces = faces
        self.groups = {}
        for face in faces:
            self.groups.setdefault(face.group, []).append(face)

        self.calc_normals()

    def add_child(self, child):
        child.parent = self
        self.children.append(child)

    def share_vertex(self, faces, vertex):
        return [face for face in faces if vertex in face]

    def avg_normal(self, faces):
        normal = Vec3()
        for face in faces:
            normal = normal + face.normal
        normal = normal / float(len(faces))
        return normal.normalize()

    def avg_tangent(self, faces):
        tangent = Vec3()
        for face in faces:
            tangent = tangent + face.tangent
        #tangent = tangent / float(len(faces))
        #return tangent.normalize()
        return tangent

    def calc_normals(self):
        for group, faces in self.groups.items():
            for face in faces:
                shared = self.share_vertex(faces, face.v1)
                normal = face.v1.normal = self.avg_normal(shared)
                tangent = self.avg_tangent(shared)
                face.v1.tangent = (tangent - normal * tangent.dot(normal)).normalize()
                face.v1.bitangent = face.v1.tangent.cross(face.v1.normal)
                #face.v1.tangent *= 1.0 if normal.cross(tangent).dot(face.bitangent) > 0.0 else -1.0
                
                shared = self.share_vertex(faces, face.v2)
                normal = face.v2.normal = self.avg_normal(shared)
                tangent = self.avg_tangent(shared)
                face.v2.tangent = (tangent - normal * tangent.dot(normal)).normalize()
                face.v2.bitangent = face.v2.tangent.cross(face.v2.normal)
                #face.v2.tangent *= 1.0 if normal.cross(tangent).dot(face.bitangent) > 0.0 else -1.0
                
                shared = self.share_vertex(faces, face.v3)
                normal = face.v3.normal = self.avg_normal(shared)
                tangent = self.avg_tangent(shared)
                face.v3.tangent = (tangent - normal * tangent.dot(normal)).normalize()
                face.v3.bitangent = face.v3.tangent.cross(face.v3.normal)
                #face.v3.tangent *= 1.0 if normal.cross(tangent).dot(face.bitangent) > 0.0 else -1.0

    def log(self, indent=0):
        print '  '*indent + self.name
        for child in self.children:
            child.log(indent+1)

    def data(self, positions, texcoords, normals, tangents, bitangents, bones):
        center = self.center*scale
        trans = self.get_trans()

        for face in self.faces:
            positions.extend(face.v1.pos*scale-center)
            texcoords.extend(face.v1.uv)
            normals.extend(face.v1.normal)
            tangents.extend(face.v1.tangent)
            bitangents.extend(face.v1.bitangent)
            
            positions.extend(face.v2.pos*scale-center)
            texcoords.extend(face.v2.uv)
            normals.extend(face.v2.normal)
            tangents.extend(face.v2.tangent)
            bitangents.extend(face.v2.bitangent)
            
            positions.extend(face.v3.pos*scale-center)
            texcoords.extend(face.v3.uv)
            normals.extend(face.v3.normal)
            tangents.extend(face.v3.tangent)
            bitangents.extend(face.v3.bitangent)

            bones.extend(trans)
            bones.extend(trans)
            bones.extend(trans)

        for child in self.children:
            child.data(positions, texcoords, normals, tangents, bitangents, bones)

    def get_local_offset(self):
        if self.parent:
            return (self.center - self.parent.center)*scale
        else:
            return Vec3(0.0, 0.0, 0.0)

    def get_trans(self):
        trans = []
        node = self
        while node.parent:
            trans.insert(0, node.index)
            node = node.parent
        while len(trans) < 4:
            trans.append(0)
        return trans

class Model:
    def __init__(self, root):
        self.root = root

    @staticmethod
    def open(filename, bones=None):
        infile = File3Ds.open(filename)
        objects = []
        objs = infile.main.children.editor.children.object

        if not isinstance(objs, list): #FIXME
            objs = [objs]

        for index, obj in enumerate(objs):
            name = obj.data.name
            mesh = obj.children.mesh
            faces = mesh.children.faces
            vertices = mesh.children.vertices
            texcoords = mesh.children.texcoords
            center = mesh.children.matrix.data.center
            groups = faces.children.smoothgroup.data.groups
            facelist = []
            for i, (i1, i2, i3, flags) in enumerate(faces.data.faces):
                group = groups[i]
                pos1 = vertices.data.vertices[i1]
                pos2 = vertices.data.vertices[i2]
                pos3 = vertices.data.vertices[i3]
                uv1 = texcoords.data.texcoords[i1]
                uv2 = texcoords.data.texcoords[i2]
                uv3 = texcoords.data.texcoords[i3]
                v1 = Vertex(i1, pos1, uv1)
                v2 = Vertex(i2, pos2, uv2)
                v3 = Vertex(i3, pos3, uv3)
                facelist.append(Face(group, v1, v2, v3))
            objects.append(Object(index, name, center, facelist))
        
        if bones:
            root = Model.walk(bones, objects)
        else:
            root = Object(0, 'root', Vec3(), [])
            for obj in objects:
                root.add_child(obj)

        return Model(root)

    @staticmethod
    def walk(bones, objects):
        if isinstance(bones, list):
            parent = objects[bones[0]]
            for child in bones[1:]:
                child = Model.walk(child, objects)
                parent.add_child(child)
            return parent
        else:
            return objects[bones]
    
    def save(self, filename):
        positions = []
        texcoords = []
        normals = []
        tangents = []
        bitangents = []
        bones = []
        
        self.root.data(positions, texcoords, normals, tangents, bitangents, bones)
        parts = self.get_parts(self.root)

        buffer = {
            'position_3f': positions,
            'texcoord_2f': texcoords,
            'normal_3f': normals,
            'tangent_3f': tangents,
            'bitangent_3f': bitangents,
            'bone_4f': bones,
        }

        result = {
            'buffer': buffer,
            'parts': parts,
        }
        
        open(filename, 'wb').write(json.dumps(result))

    def get_parts(self, node):
        if node.parent:
            off = node.get_local_offset()
            result = {
                'offset': [off.x, off.y, off.z],
                'index': node.index,
            }
        else:
            result = {}

        for child in node.children:
            result[child.name] = self.get_parts(child)
        return result

if __name__ == '__main__':
    from optparse import OptionParser
    usage = '%prog [infile] --outfile=<outfile> --hierarchy=<json>'
    parser = OptionParser(usage)
    parser.add_option('-o', '--outfile',
        dest = 'outfile',
        type = 'string',
        help = 'the output file name'
    )
    parser.add_option('-r', '--hierarchy',
        dest = 'hierarchy',
        type = 'string',
        help = 'the hierarchy to use',
    )
    parser.set_defaults(
        outfile = None,
        hierarchy = None,
    )
    options, args = parser.parse_args()
    filename = args[0]

    if options.hierarchy:
        hierarchy = json.loads(options.hierarchy)
    else:
        hierarchy = None
        
    model = Model.open(filename, hierarchy)

    if options.outfile:
        model.save(options.outfile)
    else:
        model.root.log()
