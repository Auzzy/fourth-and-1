_DEFENDER_RADIUS = 0.5
_PATH_WIDTH = 5.0 / 14.0
_PATH_RADIUS = _PATH_WIDTH / 2.0
_CATCH_RADIUS = 0.5


def catch_zone(center):
    return Rect.frompoint(center, _CATCH_RADIUS)

def path_segment(start, end):
    return Rect.fromline(start, end, _PATH_RADIUS)

def defender_zone(center):
    return Rect.frompoint(center, _DEFENDER_RADIUS)


def _cmp(a, b):
    return (a > b) - (a < b)

class Rect:
    @staticmethod
    def fromline(coord1, coord2, radius):
        x1, y1 = coord1
        x2, y2 = coord2

        xslope = _cmp(x2 - x1, 0)
        yslope = _cmp(y2 - y1, 0)

        return Rect(
            (x1 + xslope * radius, y1 - yslope * radius),
            (x1 - xslope * radius, y1 + yslope * radius),
            (x2 - xslope * radius, y2 + yslope * radius),
            (x2 + xslope * radius, y2 - yslope * radius))

    @staticmethod
    def frompoint(coord, radius):
        x, y = coord
        return Rect(
            (x - radius, y - radius),
            (x + radius, y - radius),
            (x + radius, y + radius),
            (x - radius, y + radius))

    def __init__(self, *corners):
        self.corners = corners

        get_x = key=lambda coord: coord[0]
        get_y = key=lambda coord: coord[1]

        points = list(corners[:])
        self.left = min(points, key=get_x)
        points.remove(self.left)
        self.top = min(points, key=get_y)
        points.remove(self.top)
        self.right = max(points, key=get_x)
        points.remove(self.right)
        self.bottom = max(points, key=get_y)

    @property
    def bottom_edge(self):
        return (self.left, self.bottom)

    @property
    def top_edge(self):
        return (self.top, self.right)

    @property
    def left_edge(self):
        return (self.left, self.top)

    @property
    def right_edge(self):
        return (self.bottom, self.right)

    @property
    def edges(self):
        for edge in (self.bottom_edge, self.top_edge, self.left_edge, self.right_edge):
            yield edge

    def _intercept(self, edge, x):
        x1, y1 = edge[0]
        x2, y2 = edge[1]
        if x2 - x1 == 0:
            return None

        # print(f"(y2 - y1) / (x2 - x1) -> ({y2} - {y1}) / ({x2} - {x1}): {(y2 - y1) / (x2 - x1)}")
        m = (y2 - y1) / (x2 - x1)
        return m * (x - x1) + y1

    # This should work as long as "square" isn't rotated at all. I could rotate
    # the whole system such that "square" is no longer rotated. It would make
    # it reasonable to rename this to "__contains__", so the "in" operator will
    # work, but that's not worth it yet.
    def contains_square(self, square):
        '''
        print(f"RECT: {self.corners}")
        print(f"SQUARE: {square.corners}")

        print("CORNERS")
        print(f"square.right[0] < self.left[0] -> {square.right[0]} < {self.left[0]}: {square.right[0] < self.left[0]}")
        print(f"square.left[0] > self.right[0] -> {square.left[0]} > {self.right[0]}: {square.left[0] > self.right[0]}")
        print(f"square.bottom[1] < self.top[1] -> {square.bottom[1]} < {self.top[1]}: {square.bottom[1] < self.top[1]}")
        print(f"square.top[1] > self.bottom[1] -> {square.top[1]} > {self.bottom[1]}: {square.top[1] > self.bottom[1]}")
        '''
        if square.right[0] < self.left[0] or \
                square.left[0] > self.right[0] or \
                square.bottom[1] < self.top[1] or \
                square.top[1] > self.bottom[1]:
            return False

        if not any(edge[0][0] - edge[1][0] == 0 for edge in self.edges):
            '''
            print("DIAGS")
            print(f"square.top[1] > self._intercept(self.bottom_edge, square.right[0]) -> square.top[1] > self._intercept({self.bottom_edge}, {square.right[0]}) -> {square.top[1]} > {self._intercept(self.bottom_edge, square.right[0])}: {square.top[1] > self._intercept(self.bottom_edge, square.right[0])}")
            print(f"square.bottom[1] < self._intercept(self.top_edge, square.left[0]) -> square.bottom[1] < self._intercept({self.top_edge}, {square.left[0]}) -> {square.bottom[1]} < {self._intercept(self.top_edge, square.left[0])}: {square.bottom[1] < self._intercept(self.top_edge, square.left[0])}")
            print(f"square.top[1] > self._intercept(self.right_edge, square.left[0]) -> square.top[1] > self._intercept({self.right_edge}, {square.left[0]}) -> {square.top[1]} > {self._intercept(self.right_edge, square.left[0])}: {square.top[1] > self._intercept(self.right_edge, square.left[0])}")
            print(f"square.bottom[1] < self._intercept(self.left_edge, square.right[0]) -> square.bottom[1] < self._intercept({self.left_edge}, {square.right[0]}) -> {square.bottom[1]} < {self._intercept(self.left_edge, square.right[0])}: {square.bottom[1] < self._intercept(self.left_edge, square.right[0])}")
            '''
            if square.top[1] > self._intercept(self.bottom_edge, square.right[0]) or \
                    square.bottom[1] < self._intercept(self.top_edge, square.left[0]) or \
                    square.top[1] > self._intercept(self.right_edge, square.left[0]) or \
                    square.bottom[1] < self._intercept(self.left_edge, square.right[0]):
                return False

        return True
