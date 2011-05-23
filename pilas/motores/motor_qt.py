# -*- encoding: utf-8 -*-
# pilas engine - a video game framework.
#
# copyright 2010 - hugo ruscitti
# license: lgplv3 (see http://www.gnu.org/licenses/lgpl.html)
#
# website - http://www.pilas-engine.com.ar

from PySFML import sf
from pilas.simbolos import *
import cairo
import pilas
from pilas import eventos
import motor
import glob
import re

ANCHO = 640
ALTO = 480

class BaseActor:
    
    def __init__(self):
        pass

    def obtener_ancho(self):
        return self.GetSize()[0]

    def obtener_alto(self):
        return self.GetSize()[1]

    def obtener_area(self):
        return self.obtener_ancho(), self.obtener_alto()

    def definir_centro(self, x, y):
        self.SetCenter(x, y)

    def obtener_posicion(self):
        x, y = self.GetPosition()

        # Evita decir que la coordenada y=0 es y=-0
        if y == 0:
            return x, 0

        return x, -y

    def definir_posicion(self, x, y):
        self.SetPosition(x, -y)


    def obtener_escala(self):
        return self.GetScale()[0]

    def definir_escala(self, s):
        self.SetScale(s, s)

    def definir_transparencia(self, nuevo_valor):
        nivel = min(255, 255 - (nuevo_valor*128) / 50)
        nivel = max(0, nivel)
        self.SetColor(sf.Color(255, 255, 255, int(nivel)))

    def obtener_rotacion(self):
        return (- self.GetRotation()) % 360

    def definir_rotacion(self, r):
        self.SetRotation(-r % 360)
        
    def set_espejado(self, espejado):        
        self.FlipX(espejado)
        
        
class SFMLActor(sf.Sprite, BaseActor):

    def __init__(self, imagen="sin_imagen.png", x=0, y=0):

        if isinstance(imagen, str):
            imagen = pilas.imagenes.cargar(imagen)

        sf.Sprite.__init__(self, imagen)
        BaseActor.__init__(self)

    def definir_imagen(self, imagen):
        self.SetImage(imagen)

    def obtener_imagen(self):
        return self.GetImage()

    def dibujar(self, aplicacion):
        aplicacion.Draw(self)


class SFMLTexto(sf.String, BaseActor):


    def __init__(self, texto="None", x=0, y=0):
        sf.String.__init__(self, texto)
        BaseActor.__init__(self)
        self.color = pilas.colores.negro

    def obtener_texto(self):
        return self.GetText()

    def definir_texto(self, text):
        self.SetText(text)
        self._definir_eje_en_el_centro()

    def obtener_magnitud(self):
        return self.GetSize()

    def definir_magnitud(self, size):
        self.SetSize(size)
        self._definir_eje_en_el_centro()

    def _definir_eje_en_el_centro(self):
        rect = self.GetRect()
        size = (rect.GetWidth(), rect.GetHeight())
        self.SetCenter(size[0]/2, size[1]/2)

    def obtener_color(self):
        return self.GetColor()

    def definir_color(self, k):
        self.SetColor(sf.Color(*k.obtener_componentes()))

    def dibujar(self, aplicacion):
        aplicacion.Draw(self)
        
    def colisiona_con_un_punto(self, x, y):
        return False

    def obtener_ancho(self):
        rect = self.GetRect()
        return rect.GetWidth()

    def obtener_alto(self):
        rect = self.GetRect()
        return rect.GetHeight()

class SFMLSonido:

    def __init__(self, ruta):
        buff = sf.SoundBuffer()
        buff.LoadFromFile(ruta)
        self.buffer = buff
        self.sonido = sf.Sound(self.buffer)

    def reproducir(self):
        self.sonido.Play()
        
    def definir_pitch(self, pitch):
        self.sonido.SetPitch(pitch)
        
    def Play(self):
        self.reproducir()

class SFMLCanvas:
    "Representa una superficie sobre la que se puede dibujar usando cairo."

    def __init__(self, ancho, alto):
        self.ancho = ancho
        self.alto = alto
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, ancho, alto)
        self.image = sf.Image()
        self.context = cairo.Context(self.surface)
        self.actualizar()

    def actualizar(self):
        self.image.LoadFromPixels(self.ancho, self.alto, self.surface.get_data())

    def limpiar(self):
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.ancho, self.alto)
        self.context = cairo.Context(self.surface)       

class SFMLGrilla:


    def __init__(self, ruta, columnas=1, filas=1):
        self.image = pilas.imagenes.cargar(ruta)
        self.cantidad_de_cuadros = columnas * filas
        self.columnas = columnas
        self.filas = filas
        self.cuadro_ancho = self.image.GetWidth() / columnas
        self.cuadro_alto = self.image.GetHeight() / filas
        self.sub_rect = sf.IntRect(0, 0, self.cuadro_ancho, self.cuadro_alto)
        self.definir_cuadro(0)

    def definir_cuadro(self, cuadro):
        self.cuadro = cuadro

        frame_col = cuadro % self.columnas
        frame_row = cuadro / self.columnas

        dx = frame_col * self.cuadro_ancho - self.sub_rect.Left
        dy = frame_row * self.cuadro_alto - self.sub_rect.Top

        self.sub_rect.Offset(dx, dy)

    def asignar(self, sprite):
        "Define la imagen que tiene que tener el actor."

        sprite._actor.SetImage(self.image)
        sprite._actor.SetSubRect(self.sub_rect)

    def avanzar(self):
        ha_reiniciado = False
        cuadro_actual = self.cuadro + 1

        if cuadro_actual >= self.cantidad_de_cuadros:
            cuadro_actual = 0
            ha_reiniciado = True

        self.definir_cuadro(cuadro_actual)
        return ha_reiniciado

    def obtener_cuadro(self):
        return self.cuadro

    def obtener_dx(self):
        frame_col = self.cuadro % self.columnas
        dx = frame_col * self.cuadro_ancho
        return dx

    def obtener_dy(self):
        frame_row = self.cuadro / self.columnas
        dy = frame_row * self.cuadro_alto
        return dy
        
        
class Qt(motor.Motor):


    def __init__(self):
        motor.Motor.__init__(self)
        # Se usan para calcular el dx y dy del movimiento
        # del mouse porque pySFML no lo reporta de forma relativa.
        self.mouse_x = 0
        self.mouse_y = 0

    def obtener_actor(self, imagen, x, y):
        return SFMLActor(imagen, x, y)

    def obtener_texto(self, texto, x, y):
        return SFMLTexto(texto, x, y)

    def obtener_posicion_del_mouse(self):
        return (self.mouse_x, self.mouse_y)
    
    def obtener_canvas(self, ancho, alto):
        return SFMLCanvas(ancho, alto)
    
    def obtener_grilla(self, ruta, columnas, filas):
        return SFMLGrilla(ruta, columnas, filas)

    def crear_ventana(self, ancho, alto, titulo):
        
        ventana = sf.RenderWindow(sf.VideoMode(ancho, alto), titulo)
        # Define que la coordenada (0, 0) sea el centro de la ventana.
        view = ventana.GetDefaultView()
        view.SetCenter(0, 0)
        self.input = ventana.GetInput()
        self.event = sf.Event()
        self.vista_de_camara = ventana.GetDefaultView()
        self.ventana = ventana
        return ventana

    def ocultar_puntero_del_mouse(self):
        self.ventana.ShowMouseCursor(False)

    def mostrar_puntero_del_mouse(self):
        self.ventana.ShowMouseCursor(True)

    def cerrar_ventana(self):
        self.ventana.Close()

    def dibujar_circulo(self, x, y, radio, color, color_borde):
        delta = radio / 2
        circulo = sf.Shape.Circle(0, 0, delta, 
                sf.Color(*color.obtener_componentes()), 2, 
                sf.Color(*color_borde.obtener_componentes()))
        circulo.SetCenter(0, 0)
        circulo.SetPosition(x, -y)
        self.ventana.Draw(circulo)

    def pulsa_tecla(self, tecla):
        "Indica si una tecla esta siendo pulsada en este instante."

        mapa = {
                IZQUIERDA: sf.Key.Left,
                DERECHA: sf.Key.Right,
                ARRIBA: sf.Key.Up,
                ABAJO: sf.Key.Down,
                BOTON: sf.Key.Space,
                SELECCION: sf.Key.Return,
                }

        return self.input.IsKeyDown(mapa[tecla])


    def centrar_ventana(self):
        "Coloca la ventana principal en el centro del escritorio."

        vm = sf.VideoMode(100, 100)

        # Obtiene la resolución del escritorio y la ventana.
        desktop_mode = vm.GetDesktopMode()
        w, h = self.ventana.GetWidth(), self.ventana.GetHeight()

        # Calcula cual debería la coordenada para centrar la ventana.
        to_x = desktop_mode.Width/2 - w/2
        to_y = desktop_mode.Height/2 - h/2

        self.ventana.SetPosition(to_x, to_y)

    def procesar_y_emitir_eventos(self):
        "Procesa todos los eventos que la biblioteca SFML pone en una cola."
        event = self.event

        while self.ventana.GetEvent(self.event):
            if event.Type == sf.Event.Closed:
                pilas.mundo.terminar()
            if event.Type == sf.Event.KeyPressed:
                self.procesar_evento_teclado(event)

                if event.Key.Code == sf.Key.Q and event.Key.Alt:
                    pilas.mundo.terminar()
            elif event.Type == sf.Event.TextEntered:

                eventos.pulsa_tecla.send("ejecutar", codigo=unichr(event.Text.Unicode)) 
            elif event.Type == sf.Event.MouseMoved:
                # Notifica el movimiento del mouse con una señal

                x, y = event.MouseMove.X, event.MouseMove.Y

                if x > 0 and y > 0:
                    x, y = self.ventana.ConvertCoords(x, y)
                    y = -y

                    # Se asegura de los eventos de mouse esten siempre
                    # dentro de la ventana.
                    x = min(320, x)
                    y = max(y, -240)

                    dx = x - self.mouse_x
                    dy = y - self.mouse_y

                    self.mouse_x = x
                    self.mouse_y = y

                    eventos.mueve_mouse.send("ejecutar", x=x, y=y, dx=dx, dy=dy)

            elif event.Type == sf.Event.MouseButtonPressed:
                x, y = self.ventana.ConvertCoords(event.MouseButton.X, event.MouseButton.Y)
                eventos.click_de_mouse.send("ejecutar", button=event.MouseButton.Button, x=x, y=-y)
            elif event.Type == sf.Event.MouseButtonReleased:
                x, y = self.ventana.ConvertCoords(event.MouseButton.X, event.MouseButton.Y)
                eventos.termina_click.send("ejecutar", button=event.MouseButton.Button, x=x, y=-y)
            elif event.Type == sf.Event.MouseWheelMoved:
                eventos.mueve_rueda.send("ejecutar", delta=event.MouseWheel.Delta)

    def procesar_evento_teclado(self, event):
        code = event.Key.Code
        
        if code == sf.Key.P and event.Key.Alt:
            pilas.mundo.alternar_pausa()
        elif code == sf.Key.F4:
            pilas.motor.guardar_captura()
        elif code == sf.Key.F6:
            pilas.utils.listar_actores_en_consola()                
        elif code == sf.Key.F7:
            eventos.imprimir_todos()
        elif code in [sf.Key.F8, sf.Key.F9, sf.Key.F10, sf.Key.F11, sf.Key.F12]:
            pilas.mundo.depurador.pulsa_tecla(code)
        elif code == sf.Key.Escape:
            eventos.pulsa_tecla_escape.send("ejecutar")

    def actualizar_pantalla(self):
        self.ventana.Display()

    def definir_centro_de_la_camara(self, x, y):
        view = self.ventana.GetDefaultView()
        view.SetCenter(x, y)

    def obtener_centro_de_la_camara(self):
        view = self.ventana.GetDefaultView()
        return view.GetCenter()

    def pintar(self, color):
        self.ventana.Clear(sf.Color(*color.obtener_componentes()))
            
    def cargar_sonido(self, ruta):
        return SFMLSonido(ruta)

    def cargar_imagen(self, ruta):
        image = sf.Image()
        image.LoadFromFile(ruta)
        return image

    def obtener_imagen_cairo(self, imagen):
        """Retorna una superficie de cairo representando a la imagen.

        Esta funcion es util para pintar imagenes sobre una pizarra
        o el escenario de un videojuego.
        """
        import array

        pixels = array.array("B", imagen.GetPixels())

        w = imagen.GetWidth()
        h = imagen.GetHeight()

        return cairo.ImageSurface.create_for_data(pixels, cairo.FORMAT_RGB24, w, h)

    def guardar_captura(self):
        imagen = self.ventana.Capture()
        numero = self._obtener_numeracion_siguiente_imagen()
        nombre = "imagen_%d.png" %(numero)
        imagen.SaveToFile(nombre)
        print "Guardando el archivo %s" %(nombre)

    def _obtener_numeracion_siguiente_imagen(self):
        "Obtiene un numero de imagen para guardar una captura."
        lista_de_archivos = glob.glob("imagen_*.png")

        if lista_de_archivos:
            archivos = "\n".join(lista_de_archivos)
            patron = "_(.+).png"
            numeros = [int(x) for x in re.findall(patron, archivos)]
            numeros.sort()
            ultimo_numero = numeros[-1] + 1
        else:
            ultimo_numero = 1

        return ultimo_numero