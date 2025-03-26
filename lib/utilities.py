import numpy as np

from collections import namedtuple

class Point:
    __slots__ = ('x', 'y')

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __key(self):
        return (self.x, self.y)

    def __hash__(self):
        return hash(self.__key())

    def __str__(self):
        return f"{self.x},{self.y}" 

    def __eq__(self, pt):
        return self.x == pt.x and self.y == pt.y

origin = Point(0,0)

def pt_add(pt1: Point, pt2: Point) -> Point:
    """
    Add two points together
    """
    return Point(pt1.x + pt2.x, pt1.y + pt2.y)

def pt_sub(pt1: Point, pt2: Point) -> Point:
    """
    Subtract pt2 from pt1
    """
    return Point(pt1.x - pt2.x, pt1.y - pt2.y)

def rotate_then_translate(pt: Point, angle, offset: Point, origin: Point=origin):
    """
    Rotate a point counterclockwise by a given angle around a given origin,
    then translate it by offset.

    Parameters:
    - pt (Point): the point to rotate and then translate
    - angle (float): the angle in degrees by which to rotate the point
    - offset (Point): An x and y coordinate by which to translate the point
    - origin (Point): the point around which to perform the rotation
    """
    angle  = np.deg2rad(angle)

    qx = origin.x + np.cos(angle) * (pt.x - origin.x) - np.sin(angle) * (pt.y - origin.y)
    qy = origin.y + np.sin(angle) * (pt.x - origin.x) + np.cos(angle) * (pt.y - origin.y)

    return Point(round(qx) + offset.x, round(qy) + offset.y)