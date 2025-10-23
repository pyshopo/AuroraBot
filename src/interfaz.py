"""
Interfaz gráfica mejorada de Aurora - Diseño futurista premium
Modos: Chat y Voz con conversación continua
Versión mejorada con todas las optimizaciones
"""
import sys
import threading
import logging
import re
import time

from PySide6.QtCore import Qt, QPropertyAnimation, QThread, Signal, QTimer, QEasingCurve, QPoint
from PySide6.QtGui import QFont, QCursor, QPainter, QColor, QLinearGradient, QRadialGradient, QClipboard
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QScrollArea, QFrame, QTextEdit
)

from config.settings import WINDOW_TITLE
from src.main import escuchar, procesar_comando
from src.cerebro_ia import generar_respuesta
from gtts import gTTS
import os
import platform

# Configurar logging
logger = logging.getLogger(__name__)

# Paleta de colores futurista
COLORS = {
    'background': '#0a0e27',
    'surface': '#1a1f3a',
    'surface_light': '#252b48',
    'cyan': '#00d9ff',
    'magenta': '#bf00ff',
    'pink': '#ff0080',
    'navy': '#1a237e',
    'text': '#e0e6ff',
    'text_dim': '#8b93b8',
}

# Variables globales para controlar la reproducción de voz
voz_activa = False
detener_voz_flag = False


def limpiar_texto_para_voz(texto):
    """Limpia el texto removiendo markdown y emojis para síntesis de voz"""
    texto = re.sub(r'\*\*(.+?)\*\*', r'\1', texto)
    texto = re.sub(r'\*(.+?)\*', r'\1', texto)
    texto = re.sub(r'__(.+?)__', r'\1', texto)
    texto = re.sub(r'_(.+?)_', r'\1', texto)
    texto = re.sub(r'~~(.+?)~~', r'\1', texto)
    texto = re.sub(r'`(.+?)`', r'\1', texto)
    
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    texto = emoji_pattern.sub(r'', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    
    return texto


def hablar_interruptible(texto):
    """Función de síntesis de voz que puede ser interrumpida"""
    global voz_activa, detener_voz_flag
    
    if detener_voz_flag:
        return
    
    voz_activa = True
    temp_file = "temp_audio.mp3"
    
    try:
        tts = gTTS(text=texto, lang="es")
        tts.save(temp_file)
        
        sistema = platform.system()
        
        if sistema == "Windows":
            os.system(f'start {temp_file}')
        elif sistema == "Darwin":
            os.system(f'afplay {temp_file}')
        else:
            os.system(f'mpg123 {temp_file} > /dev/null 2>&1')
        
        # Esperar con posibilidad de interrupción
        duracion = len(texto) * 0.05
        inicio = time.time()
        while time.time() - inicio < duracion:
            if detener_voz_flag:
                if sistema == "Linux":
                    os.system("killall mpg123 > /dev/null 2>&1")
                break
            time.sleep(0.1)
        
    except Exception as e:
        logger.error(f"Error en hablar_interruptible: {e}")
    finally:
        voz_activa = False
        try:
            if os.path.exists(temp_file):
                time.sleep(0.5)
                os.remove(temp_file)
        except:
            pass


# ============== WORKER PARA CHAT ==============
class ChatWorker(QThread):
    """Worker para generar respuestas en el chat sin bloquear la UI"""
    response_ready = Signal(str)
    error_occurred = Signal(str)
    
    def __init__(self, pregunta):
        super().__init__()
        self.pregunta = pregunta
    
    def run(self):
        try:
            respuesta = generar_respuesta(self.pregunta)
            self.response_ready.emit(respuesta)
        except Exception as e:
            logger.error(f"Error al generar respuesta: {e}")
            self.error_occurred.emit("Lo siento, ocurrió un error al procesar tu mensaje.")


# ============== WORKER PARA VOZ ==============
class VoiceWorker(QThread):
    """Thread para modo voz continuo con interrupción"""
    message_received = Signal(str)
    response_ready = Signal(str)
    status_updated = Signal(str)
    should_stop = Signal()
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.pausar_escucha = False
    
    def run(self):
        global voz_activa, detener_voz_flag
        
        while self.running:
            if voz_activa or self.pausar_escucha:
                time.sleep(0.1)
                continue
            
            self.status_updated.emit("🎤 Escuchando...")
            comando = escuchar()
            
            if comando == "ERROR_MIC":
                self.status_updated.emit("❌ Error de micrófono")
                break
            
            if not comando:
                continue
            
            # Interrumpir si está hablando
            if voz_activa:
                detener_voz_flag = True
                time.sleep(0.3)
                detener_voz_flag = False
            
            self.message_received.emit(f"Tú: {comando}")
            
            if any(palabra in comando for palabra in ["adiós", "adios", "eso es todo", "termina"]):
                respuesta = "Hasta luego. Fue un placer ayudarte."
                self.response_ready.emit(respuesta)
                hablar_interruptible(limpiar_texto_para_voz(respuesta))
                self.should_stop.emit()
                break
            
            self.status_updated.emit("🧠 Procesando...")
            respuesta, _ = procesar_comando(comando)
            
            if respuesta:
                self.response_ready.emit(respuesta)
                self.status_updated.emit("💬 Respondiendo...")
                hablar_interruptible(limpiar_texto_para_voz(respuesta))
        
        self.status_updated.emit("💤 Modo voz desactivado")
    
    def stop(self):
        global detener_voz_flag
        detener_voz_flag = True
        self.running = False
        time.sleep(0.3)


# ============== INDICADOR "ESCRIBIENDO..." ==============
class TypingIndicator(QWidget):
    """Indicador animado de "Aurora está escribiendo..." """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        self.phase = 0.0
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)
        
        self.label = QLabel("Aurora está escribiendo")
        self.label.setFont(QFont("Segoe UI", 11))
        self.label.setStyleSheet(f"color: {COLORS['text_dim']}; background: transparent;")
        
        self.dot1 = QLabel("●")
        self.dot2 = QLabel("●")
        self.dot3 = QLabel("●")
        
        for dot in [self.dot1, self.dot2, self.dot3]:
            dot.setFont(QFont("Segoe UI", 14))
            dot.setFixedWidth(15)
        
        layout.addWidget(self.label)
        layout.addWidget(self.dot1)
        layout.addWidget(self.dot2)
        layout.addWidget(self.dot3)
        layout.addStretch()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(150)
    
    def update_animation(self):
        self.phase = (self.phase + 1) % 3
        
        import math
        hue_offset = (self.phase * 120) % 360
        
        for i, dot in enumerate([self.dot1, self.dot2, self.dot3]):
            if i == self.phase:
                dot.setStyleSheet(f"color: {COLORS['cyan']}; background: transparent;")
            elif i == (self.phase - 1) % 3:
                dot.setStyleSheet(f"color: {COLORS['magenta']}; background: transparent;")
            else:
                dot.setStyleSheet(f"color: {COLORS['text_dim']}; background: transparent;")


# ============== FONDO ANIMADO ==============
class AnimatedBackground(QWidget):
    """Fondo animado con gradiente líquido"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.color_phase = 0.0
        
        self.color_timer = QTimer(self)
        self.color_timer.timeout.connect(self.update_animation)
        self.color_timer.start(50)
    
    def update_animation(self):
        self.color_phase = (self.color_phase + 0.005) % 1.0
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        import math
        phase = self.color_phase * 2 * math.pi
        
        center_x = self.width() / 2 + math.cos(phase) * self.width() * 0.3
        center_y = self.height() / 2 + math.sin(phase * 0.7) * self.height() * 0.3
        
        gradient = QRadialGradient(center_x, center_y, max(self.width(), self.height()))
        
        # Transición: Azul oscuro → Magenta oscuro → Cian oscuro
        if self.color_phase < 0.33:
            t = self.color_phase / 0.33
            gradient.setColorAt(0.0, QColor(10, 14, 39))
            gradient.setColorAt(0.3, QColor(
                int(26 + (191 - 26) * t),
                int(35 + (0 - 35) * t),
                int(122 + (255 - 122) * t)
            ))
            gradient.setColorAt(1.0, QColor(10, 14, 39))
        elif self.color_phase < 0.66:
            t = (self.color_phase - 0.33) / 0.33
            gradient.setColorAt(0.0, QColor(10, 14, 39))
            gradient.setColorAt(0.3, QColor(
                int(191 + (0 - 191) * t),
                int(0 + (217 - 0) * t),
                int(255)
            ))
            gradient.setColorAt(1.0, QColor(10, 14, 39))
        else:
            t = (self.color_phase - 0.66) / 0.34
            gradient.setColorAt(0.0, QColor(10, 14, 39))
            gradient.setColorAt(0.3, QColor(
                int(0 + (26 - 0) * t),
                int(217 + (35 - 217) * t),
                int(255 + (122 - 255) * t)
            ))
            gradient.setColorAt(1.0, QColor(10, 14, 39))
        
        painter.fillRect(self.rect(), gradient)


# ============== BOTÓN LÍQUIDO ==============
class LiquidButton(QPushButton):
    """Botón circular con animación líquida de colores"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 200)  # Más pequeño
        self.color_phase = 0.0
        self.scale = 1.0
        
        self.color_timer = QTimer(self)
        self.color_timer.timeout.connect(self.update_colors)
        self.color_timer.start(30)
        
        self.scale_animation = QPropertyAnimation(self, b"scale_value")
        self.scale_animation.setDuration(3000)
        self.scale_animation.setStartValue(0.92)
        self.scale_animation.setEndValue(1.08)
        self.scale_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.scale_animation.setLoopCount(-1)
        
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    
    def start_animation(self):
        self.scale_animation.start()
    
    def stop_animation(self):
        self.scale_animation.stop()
        self.scale = 1.0
        self.update()
    
    def update_colors(self):
        self.color_phase = (self.color_phase + 0.01) % 1.0
        self.update()
    
    def get_scale_value(self):
        return self.scale
    
    def set_scale_value(self, value):
        self.scale = value
        self.update()
    
    scale_value = property(get_scale_value, set_scale_value)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        import math
        phase = self.color_phase * 2 * math.pi
        
        r1 = int(191 + (0 - 191) * abs(math.sin(phase)))
        g1 = int(0 + (217 - 0) * abs(math.sin(phase)))
        b1 = int(255)
        
        r2 = int(255 + (191 - 255) * abs(math.cos(phase)))
        g2 = int(0 + (0 - 0) * abs(math.cos(phase)))
        b2 = int(128 + (255 - 128) * abs(math.cos(phase)))
        
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0.0, QColor(r1, g1, b1))
        gradient.setColorAt(0.5, QColor(COLORS['magenta']))
        gradient.setColorAt(1.0, QColor(r2, g2, b2))
        
        size = min(self.width(), self.height()) * self.scale
        x = (self.width() - size) / 2
        y = (self.height() - size) / 2
        
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(x), int(y), int(size), int(size))
        
        painter.setPen(QColor('white'))
        painter.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())


# ============== WIDGET FLOTANTE ==============
class FloatingWidget(QWidget):
    """Widget flotante minimizado estilo Messenger"""
    clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedSize(70, 70)
        self.color_phase = 0.0
        self.dragging = False
        self.offset = QPoint()
        
        self.color_timer = QTimer(self)
        self.color_timer.timeout.connect(self.update_colors)
        self.color_timer.start(30)
        
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 90, screen.height() - 90)
    
    def update_colors(self):
        self.color_phase = (self.color_phase + 0.015) % 1.0
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        import math
        phase = self.color_phase * 2 * math.pi
        
        # Rosa → Azul marino → Cian → Magenta
        if self.color_phase < 0.25:
            t = self.color_phase / 0.25
            r = int(255 + (26 - 255) * t)
            g = int(0 + (35 - 0) * t)
            b = int(128 + (126 - 128) * t)
        elif self.color_phase < 0.5:
            t = (self.color_phase - 0.25) / 0.25
            r = int(26 + (0 - 26) * t)
            g = int(35 + (217 - 35) * t)
            b = int(126 + (255 - 126) * t)
        elif self.color_phase < 0.75:
            t = (self.color_phase - 0.5) / 0.25
            r = int(0 + (191 - 0) * t)
            g = int(217 + (0 - 217) * t)
            b = int(255)
        else:
            t = (self.color_phase - 0.75) / 0.25
            r = int(191 + (255 - 191) * t)
            g = int(0)
            b = int(255 + (128 - 255) * t)
        
        gradient = QRadialGradient(35, 35, 35)
        gradient.setColorAt(0.0, QColor(r, g, b))
        gradient.setColorAt(0.5, QColor(int(r*0.8), int(g*0.8), int(b*0.8)))
        gradient.setColorAt(1.0, QColor(int(r*0.6), int(g*0.6), int(b*0.6)))
        
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(5, 5, 60, 60)
        
        painter.setPen(QColor('white'))
        painter.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "A")
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.offset = event.pos()
    
    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(self.mapToGlobal(event.pos() - self.offset))
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            if event.pos().manhattanLength() < 10:
                self.clicked.emit()


# ============== BURBUJA DE CHAT ADAPTABLE ==============
class ChatBubble(QFrame):
    """Burbuja de mensaje estilo chat futurista con tamaño adaptable"""
    edit_requested = Signal(str)
    copy_requested = Signal(str)
    
    def __init__(self, text, is_user=True, parent=None):
        super().__init__(parent)
        self.text_content = text
        self.is_user = is_user
        
        bg_color = COLORS['magenta'] if is_user else COLORS['surface_light']
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 16px;
                padding: 0px;
                border: 1px solid {'rgba(191, 0, 255, 0.3)' if is_user else 'rgba(0, 217, 255, 0.2)'};
            }}
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 10)
        main_layout.setSpacing(8)
        
        # Texto del mensaje
        label = QLabel(text)
        label.setWordWrap(True)
        label.setFont(QFont("Segoe UI", 11))
        label.setStyleSheet(f"color: {COLORS['text']}; background-color: transparent;")
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        main_layout.addWidget(label)
        
        # Botones de acciones (solo para mensajes del usuario)
        if is_user:
            actions_layout = QHBoxLayout()
            actions_layout.setSpacing(8)
            actions_layout.setContentsMargins(0, 4, 0, 0)
            
            btn_edit = QPushButton("✏️ Editar")
            btn_copy = QPushButton("📋 Copiar")
            
            for btn in [btn_edit, btn_copy]:
                btn.setFixedHeight(28)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: rgba(255, 255, 255, 0.1);
                        border: 1px solid rgba(255, 255, 255, 0.2);
                        border-radius: 6px;
                        color: {COLORS['text']};
                        font-size: 10px;
                        padding: 4px 12px;
                    }}
                    QPushButton:hover {{
                        background: rgba(255, 255, 255, 0.2);
                    }}
                """)
            
            btn_edit.clicked.connect(lambda: self.edit_requested.emit(self.text_content))
            btn_copy.clicked.connect(lambda: self.copy_requested.emit(self.text_content))
            
            actions_layout.addWidget(btn_edit)
            actions_layout.addWidget(btn_copy)
            actions_layout.addStretch()
            
            main_layout.addLayout(actions_layout)
        
        # Ajustar ancho según contenido (máximo 70% del ancho disponible)
        self.adjustSize()


# ============== VENTANA PRINCIPAL ==============
class AuroraWindow(QWidget):
    """Ventana principal con selector de modo"""
    
    def __init__(self):
        super().__init__()
        self.voice_worker = None
        self.chat_worker = None
        self.chat_input = None
        self.liquid_button = None
        self.floating_widget = None
        self.animated_bg = None
        self.typing_indicator = None
        self.mic_recording = False
        self.configurar_ventana()
        self.crear_interfaz()
        self.mostrar_selector_modo()
    
    def configurar_ventana(self):
        self.setWindowTitle(WINDOW_TITLE)
        self.setGeometry(100, 100, 1000, 750)
        self.setStyleSheet(f"background-color: {COLORS['background']};")
    
    def crear_interfaz(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
    
    def limpiar_layout(self):
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.setParent(None)
                widget.deleteLater()
    
    def changeEvent(self, event):
        """Detectar minimización"""
        if event.type() == event.Type.WindowStateChange:
            if self.isMinimized():
                self.crear_floating_widget()
        super().changeEvent(event)
    
    def crear_floating_widget(self):
        """Crear widget flotante al minimizar"""
        if not self.floating_widget:
            self.floating_widget = FloatingWidget()
            self.floating_widget.clicked.connect(self.restaurar_ventana)
            self.floating_widget.show()
    
    def restaurar_ventana(self):
        """Restaurar ventana desde widget flotante"""
        self.showNormal()
        self.activateWindow()
        if self.floating_widget:
            self.floating_widget.close()
            self.floating_widget = None
    
    def mostrar_selector_modo(self):
        self.limpiar_layout()
        
        # Fondo animado
        self.animated_bg = AnimatedBackground(self)
        self.animated_bg.setGeometry(self.rect())
        self.animated_bg.lower()
        
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(50)
        
        titulo = QLabel("AURORA")
        titulo.setFont(QFont("Segoe UI", 72, QFont.Weight.Bold))
        titulo.setStyleSheet(f"color: {COLORS['cyan']}; background: transparent; letter-spacing: 8px;")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        subtitulo = QLabel("Asistente Inteligente")
        subtitulo.setFont(QFont("Segoe UI", 18))
        subtitulo.setStyleSheet(f"color: {COLORS['text_dim']}; background: transparent; letter-spacing: 3px;")
        subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        botones_layout = QHBoxLayout()
        botones_layout.setSpacing(30)
        
        btn_chat = QPushButton("CHAT")
        btn_voz = QPushButton("VOZ")
        
        for btn in [btn_chat, btn_voz]:
            btn.setFixedSize(200, 70)
            btn.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLORS['cyan']}, stop:1 {COLORS['magenta']});
                    color: white;
                    border: none;
                    border-radius: 35px;
                    font-weight: 700;
                    letter-spacing: 3px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLORS['magenta']}, stop:1 {COLORS['pink']});
                }}
                QPushButton:pressed {{ background: {COLORS['surface_light']}; }}
            """)
        
        btn_chat.clicked.connect(self.mostrar_modo_chat)
        btn_voz.clicked.connect(self.mostrar_modo_voz)
        
        botones_layout.addWidget(btn_chat)
        botones_layout.addWidget(btn_voz)
        
        layout.addStretch()
        layout.addWidget(titulo)
        layout.addWidget(subtitulo)
        layout.addSpacing(60)
        layout.addLayout(botones_layout)
        layout.addStretch()
        
        self.main_layout.addWidget(container)
    
    def resizeEvent(self, event):
        """Actualizar tamaño del fondo animado"""
        super().resizeEvent(event)
        if self.animated_bg:
            self.animated_bg.setGeometry(self.rect())
    
    # ============== MODO CHAT ==============
    def mostrar_modo_chat(self):
        self.limpiar_layout()
        
        container = QWidget()
        container.setStyleSheet(f"background-color: {COLORS['background']};")
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Header
        header = QHBoxLayout()
        header.setSpacing(15)
        
        titulo = QLabel("Chat con Aurora")
        titulo.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        titulo.setStyleSheet(f"color: {COLORS['cyan']}; background: transparent;")
        
        btn_volver = QPushButton("VOLVER")
        btn_volver.setFixedSize(120, 40)
        btn_volver.clicked.connect(self.volver_a_inicio)
        btn_volver.setStyleSheet(f"""
            QPushButton {{
                color: {COLORS['text']};
                background: {COLORS['surface']};
                border: 1px solid {COLORS['cyan']};
                padding: 8px 20px;
                border-radius: 20px;
                font-weight: 600;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: {COLORS['surface_light']};
                border: 1px solid {COLORS['magenta']};
            }}
        """)
        
        header.addWidget(titulo)
        header.addStretch()
        header.addWidget(btn_volver)
        
        # Área de chat con scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{ background: {COLORS['surface']}; width: 8px; border-radius: 4px; }}
            QScrollBar::handle:vertical {{ background: {COLORS['cyan']}; border-radius: 4px; }}
        """)
        
        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setSpacing(15)
        self.chat_layout.addStretch()
        scroll.setWidget(self.chat_container)
        
        # Input container
        input_container = QFrame()
        input_container.setStyleSheet(f"""
            QFrame {{ background: {COLORS['surface']}; border-radius: 25px; border: 1px solid {COLORS['surface_light']}; }}
        """)
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(15, 10, 15, 10)
        input_layout.setSpacing(10)
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Escribe tu mensaje...")
        self.chat_input.setFont(QFont("Segoe UI", 12))
        self.chat_input.setStyleSheet(f"""
            QLineEdit {{ background: transparent; border: none; color: {COLORS['text']}; padding: 8px; }}
            QLineEdit::placeholder {{ color: {COLORS['text_dim']}; }}
        """)
        self.chat_input.returnPressed.connect(self.enviar_mensaje_chat)
        
        # Botón de micrófono (toggle)
        self.btn_mic = QPushButton("🎤")
        self.btn_mic.setFixedSize(45, 45)
        self.btn_mic.setCheckable(True)
        self.btn_mic.clicked.connect(self.toggle_mic_chat)
        self.btn_mic.setStyleSheet(f"""
            QPushButton {{ background: {COLORS['surface_light']}; border: none; border-radius: 22px; color: white; font-size: 16px; }}
            QPushButton:hover {{ background: {COLORS['magenta']}; }}
            QPushButton:checked {{ background: {COLORS['cyan']}; }}
        """)
        
        # Botón enviar/pausar
        self.btn_send = QPushButton("ENVIAR")
        self.btn_send.setFixedHeight(45)
        self.btn_send.clicked.connect(self.enviar_o_pausar)
        self.btn_send.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLORS['cyan']}, stop:1 {COLORS['magenta']});
                border: none;
                border-radius: 22px;
                padding: 0 25px;
                color: white;
                font-weight: bold;
                font-size: 12px;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLORS['magenta']}, stop:1 {COLORS['pink']});
            }}
        """)
        
        input_layout.addWidget(self.chat_input)
        input_layout.addWidget(self.btn_mic)
        input_layout.addWidget(self.btn_send)
        
        main_layout.addLayout(header)
        main_layout.addWidget(scroll, 1)
        main_layout.addWidget(input_container)
        
        self.main_layout.addWidget(container)
        
        # Mensaje de bienvenida
        self.agregar_mensaje_chat("¡Hola! Soy Aurora. ¿En qué puedo ayudarte hoy?", is_user=False)
    
    def volver_a_inicio(self):
        """Volver al selector de modo"""
        self.chat_input = None
        self.chat_worker = None
        self.typing_indicator = None
        self.mostrar_selector_modo()
    
    def agregar_mensaje_chat(self, texto, is_user=True):
        """Agrega una burbuja de chat"""
        bubble = ChatBubble(texto, is_user)
        
        # Conectar señales de editar y copiar
        if is_user:
            bubble.edit_requested.connect(self.editar_mensaje)
            bubble.copy_requested.connect(self.copiar_mensaje)
        
        # Ancho adaptable (máximo 70% del ancho disponible)
        max_width = int(self.width() * 0.7)
        bubble.setMaximumWidth(max_width)
        
        container = QHBoxLayout()
        container.setContentsMargins(0, 0, 0, 0)
        if is_user:
            container.addStretch()
            container.addWidget(bubble)
        else:
            container.addWidget(bubble)
            container.addStretch()
        
        # Insertar antes del stretch final
        self.chat_layout.insertLayout(self.chat_layout.count() - 1, container)
        
        # Scroll automático
        QTimer.singleShot(50, self.scroll_to_bottom)
    
    def scroll_to_bottom(self):
        """Hacer scroll hasta el final del chat"""
        scroll_area = self.chat_container.parent()
        if isinstance(scroll_area, QScrollArea):
            scroll_bar = scroll_area.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.maximum())
    
    def mostrar_typing_indicator(self):
        """Muestra el indicador de 'escribiendo...'"""
        if not self.typing_indicator:
            self.typing_indicator = TypingIndicator()
            container = QHBoxLayout()
            container.addWidget(self.typing_indicator)
            container.addStretch()
            self.chat_layout.insertLayout(self.chat_layout.count() - 1, container)
            self.scroll_to_bottom()
    
    def ocultar_typing_indicator(self):
        """Oculta el indicador de 'escribiendo...'"""
        if self.typing_indicator:
            self.typing_indicator.setParent(None)
            self.typing_indicator.deleteLater()
            self.typing_indicator = None
    
    def enviar_mensaje_chat(self):
        """Envía mensaje de texto"""
        if not self.chat_input or self.chat_worker:
            return
        
        texto = self.chat_input.text().strip()
        if not texto:
            return
        
        # Agregar mensaje del usuario
        self.agregar_mensaje_chat(texto, is_user=True)
        self.chat_input.clear()
        
        # Cambiar botón a PAUSAR
        self.btn_send.setText("⏸ PAUSAR")
        
        # Mostrar indicador
        self.mostrar_typing_indicator()
        
        # Crear worker para generar respuesta
        self.chat_worker = ChatWorker(texto)
        self.chat_worker.response_ready.connect(self.on_response_ready)
        self.chat_worker.error_occurred.connect(self.on_response_error)
        self.chat_worker.start()
    
    def on_response_ready(self, respuesta):
        """Callback cuando la respuesta está lista"""
        self.ocultar_typing_indicator()
        self.agregar_mensaje_chat(respuesta, is_user=False)
        self.btn_send.setText("ENVIAR")
        self.chat_worker = None
    
    def on_response_error(self, error):
        """Callback cuando hay un error"""
        self.ocultar_typing_indicator()
        self.agregar_mensaje_chat(error, is_user=False)
        self.btn_send.setText("ENVIAR")
        self.chat_worker = None
    
    def enviar_o_pausar(self):
        """Enviar mensaje o pausar generación"""
        if self.chat_worker and self.chat_worker.isRunning():
            # Pausar generación
            self.chat_worker.terminate()
            self.chat_worker = None
            self.ocultar_typing_indicator()
            self.btn_send.setText("ENVIAR")
        else:
            # Enviar mensaje
            self.enviar_mensaje_chat()
    
    def toggle_mic_chat(self):
        """Toggle del micrófono en el chat"""
        if self.btn_mic.isChecked():
            # Activar grabación
            self.btn_mic.setText("⏹")
            self.chat_input.setPlaceholderText("🎤 Escuchando...")
            self.iniciar_grabacion_chat()
        else:
            # Detener grabación
            self.btn_mic.setText("🎤")
            self.chat_input.setPlaceholderText("Escribe tu mensaje...")
            self.detener_grabacion_chat()
    
    def iniciar_grabacion_chat(self):
        """Inicia la grabación de voz en el chat"""
        def escuchar_comando():
            comando = escuchar()
            
            def actualizar_ui():
                if not self.chat_input:
                    return
                
                self.btn_mic.setChecked(False)
                self.btn_mic.setText("🎤")
                
                if comando and comando != "ERROR_MIC":
                    self.chat_input.setText(comando)
                
                self.chat_input.setPlaceholderText("Escribe tu mensaje...")
            
            QTimer.singleShot(0, actualizar_ui)
        
        threading.Thread(target=escuchar_comando, daemon=True).start()
    
    def detener_grabacion_chat(self):
        """Detiene la grabación (ya manejado por el toggle)"""
        pass
    
    def editar_mensaje(self, texto):
        """Edita un mensaje (lo carga en el input)"""
        if self.chat_input:
            self.chat_input.setText(texto)
            self.chat_input.setFocus()
    
    def copiar_mensaje(self, texto):
        """Copia un mensaje al portapapeles"""
        clipboard = QApplication.clipboard()
        clipboard.setText(texto)
    
    # ============== MODO VOZ ==============
    def mostrar_modo_voz(self):
        self.limpiar_layout()
        
        threading.Thread(
            target=lambda: hablar_interruptible(limpiar_texto_para_voz("Modo voz activado. Presiona el botón para hablar.")),
            daemon=True
        ).start()
        
        container = QWidget()
        container.setStyleSheet(f"background-color: {COLORS['background']};")
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(40)
        
        # Header con título más pequeño
        header = QHBoxLayout()
        titulo = QLabel("Modo Voz")
        titulo.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))  # Más pequeño
        titulo.setStyleSheet(f"color: {COLORS['cyan']}; background: transparent; letter-spacing: 2px;")
        
        btn_volver = QPushButton("VOLVER")
        btn_volver.setFixedSize(120, 40)
        btn_volver.clicked.connect(lambda: [self.detener_voz(), self.mostrar_selector_modo()])
        btn_volver.setStyleSheet(f"""
            QPushButton {{
                color: {COLORS['text']};
                background: {COLORS['surface']};
                border: 1px solid {COLORS['cyan']};
                padding: 8px 20px;
                border-radius: 20px;
                font-weight: 600;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: {COLORS['surface_light']};
            }}
        """)
        
        header.addWidget(titulo)
        header.addStretch()
        header.addWidget(btn_volver)
        
        # Botón líquido
        self.liquid_button = LiquidButton()
        self.liquid_button.setText("INICIAR")
        self.liquid_button.clicked.connect(self.toggle_voz)
        
        # Estado
        self.voice_status = QLabel("Presiona el botón para comenzar")
        self.voice_status.setFont(QFont("Segoe UI", 15))
        self.voice_status.setStyleSheet(f"color: {COLORS['text_dim']}; background: transparent;")
        self.voice_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        main_layout.addLayout(header)
        main_layout.addStretch()
        main_layout.addWidget(self.liquid_button, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addSpacing(30)
        main_layout.addWidget(self.voice_status)
        main_layout.addStretch()
        
        self.main_layout.addWidget(container)
    
    def toggle_voz(self):
        """Toggle del modo voz"""
        if self.voice_worker and self.voice_worker.isRunning():
            self.detener_voz()
        else:
            self.iniciar_voz()
    
    def iniciar_voz(self):
        """Inicia el modo voz continuo"""
        if self.liquid_button:
            self.liquid_button.setText("DETENER")
            self.liquid_button.start_animation()
        
        self.voice_status.setText("🎤 Escuchando continuamente...")
        self.voice_status.setStyleSheet(f"color: {COLORS['cyan']}; background: transparent;")
        
        self.voice_worker = VoiceWorker()
        self.voice_worker.status_updated.connect(lambda msg: self.voice_status.setText(msg))
        self.voice_worker.should_stop.connect(self.detener_voz)
        self.voice_worker.start()
    
    def detener_voz(self):
        """Detiene el modo voz (funciona incluso si está hablando)"""
        global detener_voz_flag
        detener_voz_flag = True
        
        if self.voice_worker:
            self.voice_worker.stop()
            self.voice_worker.wait()
        
        if self.liquid_button:
            self.liquid_button.setText("INICIAR")
            self.liquid_button.stop_animation()
        
        self.voice_status.setText("Presiona el botón para reactivar")
        self.voice_status.setStyleSheet(f"color: {COLORS['text_dim']}; background: transparent;")
        
        time.sleep(0.3)
        detener_voz_flag = False


# ============== MAIN ==============
def main():
    """Función principal para ejecutar la interfaz"""
    app = QApplication(sys.argv)
    
    ventana = AuroraWindow()
    ventana.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    main()