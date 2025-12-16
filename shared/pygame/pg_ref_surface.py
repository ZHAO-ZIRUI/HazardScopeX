import pygame

class PgRefSurface:
    """PgApp 的引用 Surface 定义"""
    def __init__(self, surface: pygame.Surface | None):
        self.surface = surface

    def __call__(self) -> pygame.Surface | None:
        return self.surface
