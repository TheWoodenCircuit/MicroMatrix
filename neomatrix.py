from neopixel import NeoPixel
from machine import Pin, Timer
import time
import math

default_color = 'white'
default_brightness = 1.0  

colors = {
     'red':    (255, 0, 0),
     'blue':   (0, 0, 255),
     'green':  (0, 255, 0),
     'yellow': (255, 255, 0),
     'purple': (255, 0, 255),
     'cyan':   (0, 255, 255),
     'white':  (255, 255, 255),
     'orange': (255, 165, 0),
     'black':  (0, 0, 0)
}

def hex_to_rgb(hex):
    return tuple(int(hex[i:i+2], 16) for i in (0, 2, 4))

def get_color_tuple(val):
    if isinstance(val, str):
        val = val.lower()
        if val == "":
            return None
        if colors.get(val) is not None:
            return colors.get(val)
        return hex_to_rgb(val)
    elif isinstance(val, tuple):
        return val

class Pixel:
    def __init__(self, x, y, color, brightness):
        self.x = x
        self.y = y
        self.color = get_color_tuple(color)
        self.brightness = brightness
        
    def set_color(self, color):
        self.color = get_color_tuple(color)

class Object:
    def __init__(self, x, y, color=default_color, brightness=default_brightness):
        self._x = x
        self._y = y
        self.color = get_color_tuple(color)
        self.brightness = brightness
        self.pixels = []
        self.visible = True
        self.max_x = -1
        self.max_y = -1
        self.min_x = -1
        self.min_y = -1
        self.canvas = None

    def _autoupdate(self):
        if self.canvas != None:
            self.canvas._autoupdate()

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, x):
        delta = x - self._x
        self._x = x
        self.max_x += delta
        self.min_x += delta
        self._autoupdate()        

    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, y):
        delta = y - self._y
        self._y = y
        self.max_y += delta
        self.min_y += delta
        self._autoupdate()        
        
    def move(self, x, y):
        self._x += x
        self._y += y
        self.max_x += x
        self.min_x += x
        self.max_y += y
        self.min_y += y
        self._autoupdate()        

    def set_color(self, color):
        for pixel in self.pixels:
            pixel.set_color(color)
        self._autoupdate()        
            
    def hide(self):
        self.visible = False
        self._autoupdate()        
        
    def show(self):
        self.visible = True
        self._autoupdate()        
        
    def check_collision(self, object):
        retval = []
        if self.max_x >= object.min_x and not self.min_x > object.min_x:
            retval.append(f"RIGHT:{self.max_x} , {object.min_x}")
        if self.min_x <= object.max_x and not self.max_x > object.max_x:
            retval.append(f"LEFT:{self.min_x} , {object.max_x}")
        if self.max_y >= object.min_y:
            retval.append("TOP")
        if self.min_y <= object.max_y:
            retval.append("BOTTOM")
        return retval

class Point(Object):
    def __init__(self, x, y, color=default_color, brightness=default_brightness):
        super().__init__(x, y, color, brightness)
        self.pixels.append(Pixel(0, 0, color, brightness))
        self.min_x = x
        self.min_y = y
        self.max_x = x
        self.max_y = y

class Line(Object):
    def __init__(self, x, y, end_x, end_y, color=default_color, brightness=default_brightness):
        super().__init__(x, y, color, brightness)
        self.end_x = end_x
        self.end_y = end_y
        self.min_x = x
        self.min_y = y
        self.max_x = end_x
        self.max_y = end_y
        self._calc()
    
    def _calc(self):
        self.pixels.clear() # Remove old pixels
        x1 = self.end_x - self.x
        y1 = self.end_y - self.y
        dx = x1 if x1 >= 0 else -x1
        dy = -y1 if y1 >= 0 else y1
        sx = 1 if 0 < x1 else -1
        sy = 1 if 0 < y1 else -1
        err = dx + dy
        x = 0
        y = 0

        while True:            
            self.pixels.append(Pixel(x, y, self.color, self.brightness))
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

class HLine(Line):
    def __init__(self, x, y, length, color=default_color, brightness=default_brightness):
        super().__init__(x, y, x + length, y, color, brightness)

class VLine(Line):
    def __init__(self, x, y, length, color=default_color, brightness=default_brightness):
        super().__init__(x, y, x, y + length, color, brightness)

# Adapted from https://circuitcellar.com/resources/bresenhams-algorithm/
class Circle(Object):
    def __init__(self, x, y, r, color=default_color, brightness=default_brightness, fill_color=None):
        super().__init__(x, y, color, brightness)
        self.fill_color = fill_color
        self.r = r
        self._calc()
        self.min_x = -r + x
        self.min_y = -r + y
        self.max_x = r + x
        self.max_y = r + y
        
    def _calc(self):
        self.pixels.clear()
        if self.r > 0:
            if (self.r < 1):
                self.pixels.append(Pixel(0, 0, self.color, self.brightness))
            else:
                x = -self.r
                y = 0
                err = 2 - (2 * self.r)
                while True:
                    self.pixels.append(Pixel(-x, y, self.color, self.brightness))
                    self.pixels.append(Pixel(-y, -x, self.color, self.brightness))
                    self.pixels.append(Pixel(x, -y, self.color, self.brightness))
                    self.pixels.append(Pixel(y, x, self.color, self.brightness))
                    temp = err
                    if temp > x:
                        x += 1
                        err += x * 2 + 1
                    if temp <= y:
                        y += 1
                        err += y * 2 + 1
                    if x >= 0:
                        break
                if self.fill_color != None:
                    min_y = [None for i in range(self.r+1)]
                    for pixel in self.pixels:
                        if pixel.x >= 0 and pixel.y >= 0 and (min_y[pixel.x]==None or pixel.y < min_y[pixel.x]):
                            min_y[pixel.x] = pixel.y
                    for _x in range(0, self.r):
                        for _y in range(min_y[_x]): # type: ignore
                            self.pixels.append(Pixel(_x, _y, self.fill_color, self.brightness))
                            self.pixels.append(Pixel(_x, -_y, self.fill_color, self.brightness))
                            self.pixels.append(Pixel(-_x, _y, self.fill_color, self.brightness))
                            self.pixels.append(Pixel(-_x, -_y, self.fill_color, self.brightness))
        self._autoupdate()

    @property
    def radius(self):
        return self.r
        
    @radius.setter
    def radius(self, r):
        self.r = r
        self._calc()
        
# TODO: Use property setter/getter (width,height,fill_color)
class Rectangle(Object):
    def __init__(self, x, y, width, height, color=default_color, brightness=default_brightness, fill_color=None):
        super().__init__(x, y, color, brightness)
        self.width = width
        self.height = height
        self.fill_color=fill_color
        self._calc()
    
    def _calc(self):
        # Example:
        #
        # 4 *********
        # 3 *       *
        # 2 *       *
        # 1 *       *
        # 0 *********
        #   012345678
        #
        # xpos=0, ypos=0, width=9, height=5
        #
        # top:    [0, height-1], [1, height-1], ..., [width-1,height-1]
        # bottom: [0,0], [1,0], ..., [width-1,0]
        # left:   [0,1], [0,2], ..., [0,height-2]
        # right:  [width-1,1], [width-1,2], ..., [width-1,height-2]
        #
        self.pixels.clear()
        self.min_x = 0
        self.min_y = 0
        self.max_x = self.width - 1
        self.max_y = self.height - 1
        for x in range(self.width):
            # bottom
            self.pixels.append(Pixel(x, 0, self.color, self.brightness))
            # top
            self.pixels.append(Pixel(x, self.height - 1, self.color, self.brightness))
        for y in range(1, self.height - 1):
            # left
            self.pixels.append(Pixel(0, y, self.color, self.brightness))
            #right
            self.pixels.append(Pixel(self.width - 1, y, self.color, self.brightness))
        if self.fill_color != None:
            for y in range(1, self.height - 1):
                for x in range(1,self.width-1):
                    self.pixels.append(Pixel(x, y, self.fill_color, self.brightness))

class SpriteGroup(Object):

    def __init__(self, x, y, shapes, brightness=default_brightness):
        super().__init__(x, y, "", brightness)
        x_offset = 0
        self.max_y = 0
        for shape in shapes:
            for pixel in shape.pixels:
                pixel.x += x_offset
                self.pixels.append(pixel)
            x_offset += shape.max_x + 1
            if shape.max_y > self.max_y:
                self.max_y = shape.max_y
        self.min_x = 0
        self.min_y = 0
        self.max_x = x_offset

class Sprite(Object):

    def __init__(self, x, y, shape, color_map, brightness=default_brightness):
        super().__init__(x, y, "", brightness)
        self.color_map = color_map
        self.objects = []
        self.image_index = -1
        if isinstance(shape, list):
            for _shape in shape:
                self.objects.append(self._read_object(_shape))
        else:
            self.objects.append(self._read_object(shape))
        self.next_image()

    def _read_object(self, shape):
        x = 0
        y = shape.count('\n') - 2
        obj = Object(None, None)
        obj.min_x = 0
        obj.min_y = 0   
        obj.max_y = y
        obj.max_x = 0
        for pos in range(len(shape)):
            c = shape[pos]
            if c == "\n":
                x = 0
                y -= 1
            else:
                if c != ' ':
                    obj.pixels.append(Pixel(x, y, self.color_map[c], self.brightness))
                x += 1
                if x > obj.max_x:
                    obj.max_x = x   
        return obj 
    
    def next_image(self):
        self.image_index += 1
        if self.image_index == len(self.objects):
            self.image_index = 0
        self.pixels = self.objects[self.image_index].pixels
        self.max_x =  self.objects[self.image_index].max_x
        self.max_y =  self.objects[self.image_index].max_y
        self._autoupdate()

class Canvas:
    def __init__(self, height=16, width=16, pin=28, autoupdate=False):
        self.objects = []
        self.width = width
        self.height = height
        self.num_pixels = height * width
        self.leds = NeoPixel(Pin(pin, Pin.OUT), self.num_pixels)
        self.color_array = [[(0, 0, 0) for i in range(self.height)] for j in range(self.width)]
        self.brightness_array = [[10 for i in range(self.height)] for j in range(self.width)]
        self.autoupdate = autoupdate
    
    def _autoupdate(self):
        if self.autoupdate:
            self.update()

    def add(self, o):
        if isinstance(o, list):
            for object in o:
                self.objects.append(object)
                object.canvas = self
        else:
            self.objects.append(o)
            o.canvas = self
        self._autoupdate()

    def remove(self, object,update=True):
        self.objects.remove(object)
        self._autoupdate()

    def remove_all(self,update=True):
        self.objects.clear()
        self._autoupdate()

    def update(self):
        color_array = [[(0,0,0) for j in range(self.height)] for i in range(self.width)]
        brightness_array = [[0 for j in range(self.height)] for i in range(self.width)]
        for object in self.objects:
            if object.visible:
                for pixel in object.pixels:
                    x = pixel.x + math.floor(object.x)
                    y = pixel.y + math.floor(object.y)
                    if x >= 0 and x < self.width and y >= 0 and y < self.height:
                        color_array[x][y]= pixel.color
                        brightness_array[x][y]= pixel.brightness
        for y in range(self.height):
            for x in range(self.width):
                if y % 2 == 0:
                    i = (y * self.width) + x
                else:
                    i = (y * self.width) + (self.width - 1) - x
                self.leds[i] = (
                    round(color_array[x][y][0] * brightness_array[x][y] / 100), 
                    round(color_array[x][y][1] * brightness_array[x][y] / 100), 
                    round(color_array[x][y][2] * brightness_array[x][y] / 100))
        self.leds.write()
       
    #TODO: this should be applied to the shapes 
    def set_brightness(self, brightness):
        for y in range(self.height):
            for x in range(self.width):
                self.brightness_array[x][y] = brightness
        self._autoupdate()
        
    def valid_coord(self, x, y):
        return x >= 0 and x < self.width and y >= 0 and y < self.height
        
    # Adapted from https://www.geeksforgeeks.org/flood-fill-algorithm-implement-fill-paint/
    # TODO: Re-implement, or get rid of
    def fill(self, xpos, ypos, color, brightness):
      color = get_color_tuple(color)
      # Visiting array
      vis = [[0 for i in range(self.height)] for j in range(self.width)]
         
      # Creating queue for bfs
      obj = []
         
      # Pushing pair of {x, y}
      obj.append([xpos, ypos])
         
      # Marking {x, y} as visited
      vis[xpos][ypos] = 1
         
      # Until queue is empty
      while len(obj) > 0:
         
        # Extracting front pair
        coord = obj[0]
        x = coord[0]
        y = coord[1]
        prev_color = self.color_array[x][y]
       
        #self.draw_point(x, y, color, brightness)
        # Popping front pair of queue
        obj.pop(0)
       
        # For right side Pixel or Cell
        if self.valid_coord(x+1, y) and vis[x + 1][y] == 0 and self.color_array[x+1][y] == prev_color:
          obj.append([x + 1, y])
          vis[x + 1][y] = 1
           
        # For left side Pixel or Cell
        if self.valid_coord(x-1, y) and vis[x - 1][y] == 0 and self.color_array[x-1][y] == prev_color:
          obj.append([x - 1, y])
          vis[x - 1][y] = 1
           
        # For upside Pixel or Cell
        if self.valid_coord(x, y+1) and vis[x][y + 1] == 0 and self.color_array[x][y+1] == prev_color:
          obj.append([x, y + 1])
          vis[x][y + 1] = 1
           
        # For downside side Pixel or Cell
        if self.valid_coord(x, y-1) and vis[x][y - 1] == 0 and self.color_array[x][y-1] == prev_color:
          obj.append([x, y - 1])
          vis[x][y - 1] = 1         
