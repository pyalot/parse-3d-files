'''
    Description: This file implements the ms3d file format and conversion to json.
    Status: incomplete, parsing of bones, groups, joints etc. is not done.
    License: AGPLv3, see LICENSE for more details
    Copyright: 2011 Florian Boesch <pyalot@gmail.com>
    Helpful Links:
        http://chumbalum.swissquake.ch/ms3d/ms3dspec.txt
        http://en.wikipedia.org/wiki/MilkShape_3D
        http://content.gpwiki.org/index.php/MS3D
'''

from ctypes import Structure, c_char, c_int, c_char_p, c_void_p, cast, c_ushort, sizeof, c_byte, c_float, c_uint
from vector import Vec2, Vec3

class Array(object):
    def __init__(self, address, amount, type):
        self.type       = type
        self.address    = address
        self.amount     = amount
        self.size       = sizeof(type)
        self.end = self.address + amount * self.size

    def from_address(self, address):
        return self.type.from_address(address)

    def __iter__(self):
        for address in xrange(self.address, self.end, self.size):
            yield self.from_address(address)

    def __getitem__(self, item):
        if isinstance(item, slice):
            indices = item.indices(self.amount)
            return [
                self.from_address(self.address + index*self.size)
                for index in range(*indices)
            ]
        else:
            if item < 0:
                item = self.amount - item
                return self.from_address(self.address + item*self.size)
            else:
                return self.from_address(self.address + item*self.size)

class MSStruct(Structure):
    _pack_ = 1

class Header(MSStruct):
    _fields_ = [
        ('id'       , c_char*10),
        ('version'  , c_int),
    ]

class Vertex(MSStruct):
    _fields_ = [
        ('flags'    , c_byte),
        ('x'        , c_float),
        ('y'        , c_float),
        ('z'        , c_float),
        ('bone'     , c_byte),
        ('refcount' , c_byte),
    ]

class Vector(MSStruct):
    _fields_ = [
        ('x'        , c_float),
        ('y'        , c_float),
        ('z'        , c_float),
    ]

class Triangle(MSStruct):
    _fields_ = [
        ('flags'    , c_ushort),
        ('v1'       , c_ushort),
        ('v2'       , c_ushort),
        ('v3'       , c_ushort),
        ('n1'       , Vector),
        ('n2'       , Vector),
        ('n3'       , Vector),
        ('s1'       , c_float),
        ('s2'       , c_float),
        ('s3'       , c_float),
        ('t1'       , c_float),
        ('t2'       , c_float),
        ('t3'       , c_float),
        ('smoothing_group'  , c_byte),
        ('group_index'      , c_byte),
    ]

class GroupHeader(MSStruct):
    _fields_ = [
        ('flags',           c_byte),
        ('name',            c_char*32),
        ('num_triangles',   c_ushort),
    ]

class Group:
    def __init__(self, address):
        self.header = GroupHeader.from_address(address)
        self.triangle_indices = (c_ushort*self.header.num_triangles).from_address(address + sizeof(GroupHeader))
        self.material_index = c_byte.from_address(address + sizeof(GroupHeader) + sizeof(self.triangle_indices))
        self.end = address + sizeof(GroupHeader) + sizeof(self.triangle_indices) + sizeof(c_byte)

class Color(MSStruct):
    _fields_ = [
        ('r',   c_float),
        ('g',   c_float),
        ('b',   c_float),
        ('a',   c_float),
    ]

class Material(MSStruct):
    _fields_ = [
        ('name'         , c_char*32),
        ('ambient'      , Color),
        ('diffuse'      , Color),
        ('specular'     , Color),
        ('emissive'     , Color),
        ('shinyness'    , c_float),
        ('transparency' , c_float),
        ('mode'         , c_byte),
        ('texture'      , c_char*128),
        ('alphamap'     , c_char*128),
    ]


class Joint:
    class Frame(MSStruct):
        _fields_ = [
            ('time'     , c_float),
            ('vec'      , Vector),
        ]
    class Header(MSStruct):
        _fields_ = [
            ('flags'        , c_byte),
            ('name'         , c_char*32),
            ('parentName'   , c_char*32),
            ('rotation'     , Vector),
            ('position'     , Vector),
            ('rot_count'    , c_ushort),
            ('pos_count'    , c_ushort),
        ]
    def __init__(address):
        self.header = Joint.Header.from_address(address)
        self.rotations = Array(
            type    = Joint.Frame,
            address = address + sizeof(Joint.Header),
            amount  = self.header.rot_count.value,
        )
        self.positions = Array(
            type    = Joint.Frame,
            address = self.rotations.end,
            amount  = self.header.pos_count.value,
        )
        self.end = self.positions.end

class VertexExtra1(MSStruct):
    _fields_ = [
        ('bones',   c_byte*3),
        ('weights', c_byte*3),
    ]

class MS3DFile:
    @staticmethod
    def open(name):
        data = open(name, 'rb').read()
        return MS3DFile(data)

    def __init__(self, data):
        self.data = data
        self.start = cast(c_char_p(self.data), c_void_p).value
        self.header = Header.from_address(self.start)
        vertex_count = c_ushort.from_address(self.start + sizeof(Header))
        self.vertices = Array(
            type    = Vertex,
            address = self.start + sizeof(Header) + sizeof(c_ushort),
            amount  = vertex_count.value,
        )

        triangle_count = c_ushort.from_address(self.vertices.end)
        self.triangles = Array(
            type    = Triangle,
            address = self.vertices.end + sizeof(c_ushort),
            amount  = triangle_count.value,
        )

        group_count = c_ushort.from_address(self.triangles.end)
        self.groups = []
        addr = self.triangles.end+sizeof(c_ushort)
        for i in range(group_count.value):
            self.groups.append(Group(addr))
            addr = self.groups[-1].end

        material_count = c_ushort.from_address(addr)
        self.materials = Array(
            type    = Material,
            address = addr + sizeof(c_ushort),
            amount  = material_count.value,
        )

        addr = self.materials.end

        self.fps = c_float.from_address(addr)
        addr += sizeof(c_float)

        self.current_time = c_float.from_address(addr)
        addr += sizeof(c_float)

        self.frame_count = c_int.from_address(addr)
        addr += sizeof(c_int)

        joint_count = c_ushort.from_address(addr)
        addr += sizeof(c_ushort)

        self.joints = []
        for i in range(joint_count.value):
            joint = Joint(addr)
            self.joints.append(joint)
            addr = joint.end

        sub_version = c_int.from_address(addr) # should be 1
        addr += sizeof(c_int)

        group_comment_count = c_uint.from_address(addr)
        addr += sizeof(c_uint)
        #fixme implement group comments (count is currently 0)

        material_comment_count = c_int.from_address(addr)
        addr += sizeof(c_int)
        #fixme implement material comments (count is currently 0)

        joint_comment_count = c_int.from_address(addr)
        addr += sizeof(c_int)
        #fixme implement joint comments (count is currently 0)

        model_comment_count = c_int.from_address(addr)
        addr += sizeof(c_int)
        #fixme implement model comments (count is currently 0)

        sub_version = c_int.from_address(addr).value
        addr += sizeof(c_int)

        if sub_version == 1:
            extra_type = VertexExtra1
        elif sub_version == 2:
            raise NotImplemented()

        self.vertex_extras = Array(
            type    = extra_type,
            address = addr,
            amount  = vertex_count.value,
        )
        addr = self.vertex_extras.end

        assert addr - self.start == len(data)
        # file endshere
        #sub_version = c_int.from_address(addr).value
        #addr += sizeof(c_int)

    @staticmethod
    def get_tangent(normal, v1, v2, uv1, uv2):
        #taken from http://fabiensanglard.net/bumpMapping/index.php
        div = (uv1.x * uv2.y - uv2.x * uv1.y)
        if div != 0.0:
            coef = 1.0/div
            x = coef * ((v1.x * uv2.y) + (v2.x * -uv1.y))
            y = coef * ((v1.y * uv2.y) + (v2.y * -uv1.y))
            z = coef * ((v1.z * uv2.y) + (v2.z * -uv1.y))
            return x, y, z
        else:
            return 0.0, 0.0, 1.0

    def get_triangle(self, index):
        triangle = self.triangles[index]

        v1 = self.vertices[triangle.v1]
        v1 = v1.x, v1.y, v1.z
        n1 = triangle.n1
        n1 = n1.x, n1.y, n1.z
        uv1 = triangle.s1, triangle.t1
        
        v2 = self.vertices[triangle.v2]
        v2 = v2.x, v2.y, v2.z
        n2 = triangle.n2
        n2 = n2.x, n2.y, n2.z
        uv2 = triangle.s2, triangle.t2
        
        v3 = self.vertices[triangle.v3]
        v3 = v3.x, v3.y, v3.z
        n3 = triangle.n3
        n3 = n3.x, n3.y, n3.z
        uv3 = triangle.s3, triangle.t3

        t1 = self.get_tangent(Vec3(*n1), Vec3(*v2)-Vec3(*v1), Vec3(*v3)-Vec3(*v1), Vec2(*uv2)-Vec2(*uv1), Vec2(*uv3)-Vec2(*uv1))
        t2 = self.get_tangent(Vec3(*n2), Vec3(*v3)-Vec3(*v2), Vec3(*v1)-Vec3(*v2), Vec2(*uv3)-Vec2(*uv2), Vec2(*uv1)-Vec2(*uv2))
        t3 = self.get_tangent(Vec3(*n3), Vec3(*v1)-Vec3(*v3), Vec3(*v2)-Vec3(*v3), Vec2(*uv1)-Vec2(*uv3), Vec2(*uv2)-Vec2(*uv3))

        return [
            (v1, n1, uv1, t1),
            (v2, n2, uv2, t2),
            (v3, n3, uv3, t3),
        ]

    def get_group(self, group):
        positions = []
        normals = []
        texcoords = []
        tangents = []
        for index in group.triangle_indices:
            triangle = self.get_triangle(index)
            for pos, normal, uv, tangent in triangle:
                positions.extend(pos)
                normals.extend(normal)
                texcoords.extend(uv)
                tangents.extend(tangent)

        return positions, normals, texcoords, tangents

if __name__ == '__main__':
    import json, sys
    filename = sys.argv[1]
    infile = MS3DFile.open(filename)

    positions = []
    normals = []
    texcoords = []
    tangents = []
    for group in infile.groups:
        position, normal, texcoord, tangent = infile.get_group(group)
        positions.extend(position)
        normals.extend(normal)
        texcoords.extend(texcoord)
        tangents.extend(tangent)

    result = {
        'position_3f': positions,
        'normal_3f': normals,
        'tangent_3f': tangents,
        'texcoord_2f': texcoords,
    }
    print json.dumps(result)
