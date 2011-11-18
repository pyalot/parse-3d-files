'''
    A vector helper
    License: AGPLv3, see LICENSE for more details
    Copyright: 2011 Florian Boesch <pyalot@gmail.com>
'''
class Vec2:
    def __init__(self, x=0, y=0):
        self.x = float(x)
        self.y = float(y)

    def __sub__(self, other):
        return Vec2(
            self.x - other.x,
            self.y - other.y,
        )

    def __iter__(self):
        return iter((self.x, self.y))

class Vec3:
    def __init__(self, x=0, y=0, z=0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def cross(s, o):
        return Vec3(
            s.y*o.z - o.y*s.z,
            s.z*o.x - o.z*s.x,
            s.x*o.y - o.x*s.y,
        )

    def dot(s, o):
        return s.x*o.x + s.y*o.y + s.z*o.z
    
    def __sub__(self, other):
        return Vec3(
            self.x - other.x,
            self.y - other.y,
            self.z - other.z,
        )
    
    def __add__(self, other):
        return Vec3(
            self.x + other.x,
            self.y + other.y,
            self.z + other.z,
        )

    def __iadd__(self, other):
        self.x += other.x
        self.y += other.y
        self.z += other.z
        return self

    def __mul__(self, scalar):
        return Vec3(
            self.x * scalar,
            self.y * scalar,
            self.z * scalar,
        )

    def __div__(self, scalar):
        return Vec3(
            self.x / scalar,
            self.y / scalar,
            self.z / scalar,
        )

    def __idiv__(self, scalar):
        self.x /= scalar
        self.y /= scalar
        self.z /= scalar
        return self

    def normalize(self):
        length = (self.x*self.x + self.y*self.y + self.z*self.z)**0.5
        return Vec3(
            self.x/length,
            self.y/length,
            self.z/length,
        )

    def __iter__(self):
        return iter((self.x, self.y, self.z))
