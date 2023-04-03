# Import Required Libraries
import pygame as pg
import pygame.gfxdraw as gfx
import pymunk as pm
import pymunk.pygame_util as pmg
import math
import numpy as np
from scipy.interpolate import interp1d
import pygame.mask


# Initialize PyGame
pg.init()

# Set Up Window
WIDTH, HEIGHT = 1280, 720
window = pg.display.set_mode((WIDTH, HEIGHT), pg.HWSURFACE  | pg.DOUBLEBUF | pg.HWACCEL)

# Create pymunk space
space = pm.Space()

# Background Image
background_image = pg.image.load('background.png')
background_image = pg.transform.scale(background_image, (WIDTH, HEIGHT))


# Texture
image = pg.image.load("texture.png")

# Draw The Simulation


def draw(space, window, draw_options, wave):
    window.fill("black")
    window.fill((240, 248, 255))

    window.blit(background_image, (0, 0))

    # ====================================
    # Create Smooth Curve
    # ====================================

    # FFT

    # Extract x and y coordinates from the points
    # x_coords = [point.body.position[0] for point in wave]
    # y_coords = [point.body.position[1] for point in wave]

    # Numpy for speed 
    x_coords = np.array([point.body.position[0] for point in wave])
    y_coords = np.array([point.body.position[1] for point in wave])
    # Numpy for speed 

    # Compute the FFT of the y-coordinates
    y_fft = np.fft.fft(y_coords)

    # Apply a low-pass filter by zeroing out higher frequency components
    cutoff = 6  # Modify this value to adjust the smoothness of the filtered line
    y_fft[cutoff:-cutoff] = 0

    # Compute the inverse FFT to obtain the filtered y-coordinates
    y_filtered = np.fft.ifft(y_fft)


    # Draw Water Underneath Curve
    # Create a list of vertices for the polygon representing the area under the curve
    # vertices = [(x_coords[i], y_filtered[i].real)
                # for i in range(len(x_coords))]
    # vertices += [(x_coords[-1], HEIGHT), (x_coords[0], HEIGHT)]

    # Numpy for speed
    vertices = np.array([(x_coords[i], y_filtered[i].real) for i in range(len(x_coords))])
    vertices = np.append(vertices, [(x_coords[-1], HEIGHT), (x_coords[0], HEIGHT)], axis=0)

    # pg.draw.polygon(window, (64, 80, 92, 50), vertices)
    
    # METHOD 1 - Fastest
    # pg.gfxdraw.filled_polygon(window, vertices,(14,49,81, 200))
    # pg.gfxdraw.aapolygon(window, vertices, (14,49,81, 255))

    # METHOD 2 - Realistic, slower but not blizting the AA edge looks and performs pretty good 
    # Create a new surface with alpha channel
    image_surface = pg.Surface((image.get_width(), image.get_height()), pg.SRCALPHA)

    # Blit the image onto the surface
    image_surface.blit(image, (0, 0))

    # Create a new surface for the polygon
    polygon_surface = pg.Surface((WIDTH,HEIGHT), pg.SRCALPHA)

    # Draw the polygon onto the surface
    pg.gfxdraw.filled_polygon(polygon_surface, vertices, (255, 255, 255, 255))
    # pg.gfxdraw.aapolygon(polygon_surface, vertices, (14,49,81, 255))

    # Blit the image surface onto the polygon surface
    polygon_surface.blit(image_surface, (0, 0), special_flags=pg.BLEND_RGBA_MULT)

    # Blit the polygon surface onto the main surface
    window.blit(polygon_surface, (0, 0))

    
    pg.gfxdraw.aapolygon(window, vertices, (124,166,203, 255))


    # ====================================
    # Create Smooth Curve
    # ====================================

    pg.display.update()


# Get Distance Between Two Points
def distance(p1, p2):
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

# ====================================
# CREATION FUNCTIONS
# ====================================

# Create Boundaries for our Simulation


def create_boundaries(space, width, height):
    rectRadius = 3
    borderColor = (255, 255, 255, 20)
    rects = [
        # Ground
        [(width/2, height-rectRadius), (width, rectRadius)],
        # Ceiling
        [(width/2, rectRadius/2), (width, rectRadius)],
        # Walls
        [(rectRadius/2, height/2), (rectRadius, height)],
        [(width-rectRadius, height/2), (rectRadius, height)],
    ]

    for pos, size in rects:
        body = pm.Body(body_type=pm.Body.STATIC)
        body.position = pos
        shape = pm.Poly.create_box(body, size)
        shape.elasticity = 0.4
        shape.friction = 0.5
        shape.color = borderColor
        shape.filled = False
        space.add(body, shape)


# ====================================
# END CREATION FUNCTIONS
# ====================================

# ====================================
# Object Classes
# ====================================

# Create Spring Points Class
class SpringPoints:
    def __init__(self, x=0, y=0, height=HEIGHT/3):
        self.dampening = 0.1
        self.tension = 0.1
        self.height = height
        self.velocity = 0
        self.x = x
        self.y = y

        self.dragging = False

        body = pm.Body(body_type=pm.Body.DYNAMIC)
        body.position = (self.x, self.y)
        # shape = pm.Circle(body, 4.5)
        shape = pm.Circle(body, 0.01)
        shape.mass = 1
        shape.elasticity = 0.5
        shape.friction = 0.2
        shape.color = (255, 255, 255, 100)

        # Spring
        b0 = pm.Body(body_type=pm.Body.KINEMATIC)
        b0.position = (int(self.x), int(HEIGHT))
        p0 = self.x, HEIGHT
        joint = pm.constraints.DampedSpring(
            # b0, body, (self.x, HEIGHT), (self.x, HEIGHT/2), HEIGHT, 50, 5)
            # b0, body, (0, 0), (0, 0), (HEIGHT/3), 10, 30)
            b0, body, (0, 0), (0, 0), (height), 0.5, 0.8)
        space.add(b0, body, shape, joint)

        self.body = body
        self.shape = shape
        self.joint = joint
        self.anchor = b0

    # ====================================
    # END Object Classes
    # ====================================


def main(window, width, height):
    # Main Loop Vars

    # Drawing Options
    draw_options = pmg.DrawOptions(window)
    draw_options.flags = pm.SpaceDebugDrawOptions.DRAW_SHAPES

    run = True
    paused = False
    clock = pg.time.Clock()
    fps = 60
    dt = 1 / fps

    # Check for Mouse Drag
    dragging = False

    # Objects to Draw
    objects = []

    # Setup Gravity for the Space
    # space.gravity = (0, 9.81 * 100)
    space.gravity = (0, 9.81 * 100 * 0)

    # Call Creation Functions
    create_boundaries(space, width, height)

    # For One Point only
    # springPoint = SpringPoints(width/2, height/2)

    # Create Wave
    # wave = [SpringPoints(loc, height/2) for loc in range(width//5)]
    intervals = np.linspace(0, WIDTH, 100)
    # intervals = np.linspace(20, WIDTH-20, 5)
    print(intervals)
    wave = [SpringPoints(loc, height/2, HEIGHT//2.4) for loc in intervals]
    # wave = [SpringPoints(width/2, height/2)]

    # Current Wave Height (change if want to account for displacement)
    # WAVEHEIGHT = 480
    # WAVEHEIGHT = 30
    WAVEHEIGHT = HEIGHT - HEIGHT *0.6667
    stiffness = 144
    damping = 5
    # Rest Length Scale
    SCALE = 1/4
    SCALE = 1/3
    SCALE = 1/2
    # SCALE = 1

    # Link Adjacent Wave Points
    for ind in range(len(wave)):
        # Join Farmost Left Point to Left Boundary
        if ind == 0:
            print(f'{wave[ind].body.position=}')
            leftBoundary = pm.Body(body_type=pm.Body.KINEMATIC)
            leftBoundary.position = (0, WAVEHEIGHT)
            print(f'{leftBoundary.position=}')
            joint = pm.constraints.DampedSpring(
                leftBoundary, wave[ind].body, (0, 0), (0, 0),
                wave[ind].x, 10, 10
            )
            joint2 = pm.constraints.DampedSpring(
                wave[ind].body, wave[ind + 1].body, (0, 0), (0, 0), distance(
                    wave[ind].body.position, wave[ind + 1].body.position)*SCALE, stiffness, damping
            )
            space.add(joint2)

            space.add(joint)

        # Join Farmost Right Point to Right Boundary
        elif ind == len(wave)-1:
            rightBoundary = pm.Body(body_type=pm.Body.KINEMATIC)
            rightBoundary.position = (WIDTH-0, WAVEHEIGHT)
            joint = pm.constraints.DampedSpring(
                wave[ind].body, rightBoundary, (0, 0), (0, 0), distance(
                    wave[ind].body.position, rightBoundary.position)*SCALE, 10, 10
            )

        # Join To Adjacent Points
        else:
            joint = pm.constraints.DampedSpring(
                wave[ind].body, wave[ind + 1].body, (0, 0), (0, 0), distance(
                    wave[ind].body.position, wave[ind + 1].body.position)*SCALE, stiffness, damping
            )
            space.add(joint)

    decreasingS = False
    increasingS = False
    decreasingD = False
    increasingD = False

    # Main Simulation Loop
    while run:
        # Get Events

        # For each point
        for springPoint in wave:
            # print(f'{springPoint.body.position=}')

            if springPoint.dragging:
                # Stop that point from moving if dragging
                springPoint.body.velocity = (0, 0)
                springPoint.joint.b.position = (
                    springPoint.joint.b.position[0], pg.mouse.get_pos()[1])

            for event in pg.event.get():
                # Handle Quite Event
                if event.type == pg.QUIT:
                    run = False
                    break

                # Handle Pausing/Playing The Simulation
                if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                    if paused:
                        paused = False
                    else:
                        paused = True

                # Adjust stiffness and damping
                if event.type == pg.KEYDOWN and event.key == pg.K_p or increasingS:
                    springPoint.joint.stiffness += 1
                    increasingS = True
                    print(f'{springPoint.joint.stiffness=}')

                if event.type == pg.KEYUP and event.key == pg.K_p:
                    increasingS = False

                if event.type == pg.KEYDOWN and event.key == pg.K_o or decreasingS:
                    springPoint.joint.stiffness -= 1
                    decreasingS = True
                    print(f'{springPoint.joint.stiffness=}')

                if event.type == pg.KEYUP and event.key == pg.K_o:
                    decreasingS = False

                if event.type == pg.KEYDOWN and event.key == pg.K_SEMICOLON or increasingD:
                    springPoint.joint.damping += 1
                    increasingD = True
                    print(f'{springPoint.joint.damping=}')

                if event.type == pg.KEYUP and event.key == pg.K_SEMICOLON:
                    increasingD = False

                if event.type == pg.KEYDOWN and event.key == pg.K_l or decreasingD:
                    springPoint.joint.springPoint.joint.damping -= 1
                    decreasingD = True
                    print(f'{springPoint.joint.damping=}')

                if event.type == pg.KEYUP and event.key == pg.K_l:
                    decreasingD = False

                # Moving Ball On Mouseclick

                # Check for drag
                if (event.type == pg.MOUSEBUTTONDOWN and event.button == 1) or dragging:
                    if springPoint.shape.point_query(pg.mouse.get_pos()):

                        # Get closest Spring Point
                        min_distance = float("inf")
                        closest_spring = None

                        for springPoint in wave:
                            dist = distance(
                                springPoint.body.position, event.pos)
                            if dist < min_distance:
                                min_distance = dist
                                closest_spring = springPoint

                        if closest_spring is not None:
                            closest_spring.dragging = True
                    print(f'{pg.mouse.get_pos()=}')

                if event.type == pg.MOUSEBUTTONUP:
                    for springPoint in wave:
                        springPoint.dragging = False

                # for springPoint in wave:
                    # if springPoint.dragging:
                        # springPoint.body.velocity = (0, 0)
                        # springPoint.joint.b.position = pg.mouse.get_pos()

        # Check for Pause/Play State
        if not paused:
            draw(space, window, draw_options, wave)
            space.step(dt)
            clock.tick(fps)

    pg.quit()


if __name__ == "__main__":
    main(window, WIDTH, HEIGHT)
