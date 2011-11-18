'''
    Description: A vector helper
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
    
    def __sub__(self, other):
        return Vec3(
            self.x - other.x,
            self.y - other.y,
            self.z - other.z,
        )
