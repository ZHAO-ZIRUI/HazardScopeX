class PgColor:
    """PgApp 的颜色定义"""

# region: W3C 基准颜色
    ALICE_BLUE                = (240, 248, 255, 255)
    ANTIQUE_WHITE             = (250, 235, 215, 255)
    AQUA                      = (0, 255, 255, 255)
    AQUAMARINE                = (127, 255, 212, 255)
    AZURE                     = (240, 255, 255, 255)
    BEIGE                     = (245, 245, 220, 255)
    BISQUE                    = (255, 228, 196, 255)
    BLACK                     = (0, 0, 0, 255)
    BLANCHED_ALMOND           = (255, 235, 205, 255)
    BLUE                      = (0, 0, 255, 255)
    BLUE_VIOLET               = (138, 43, 226, 255)
    BROWN                     = (165, 42, 42, 255)
    BURLYWOOD                 = (222, 184, 135, 255)
    CADET_BLUE                = (95, 158, 160, 255)
    CHARTREUSE                = (127, 255, 0, 255)
    CHOCOLATE                 = (210, 105, 30, 255)
    CORAL                     = (255, 127, 80, 255)
    CORNFLOWER_BLUE           = (100, 149, 237, 255)
    CORNSILK                  = (255, 248, 220, 255)
    CRIMSON                   = (220, 20, 60, 255)
    CYAN                      = (0, 255, 255, 255)
    DARK_BLUE                 = (0, 0, 139, 255)
    DARK_CYAN                 = (0, 139, 139, 255)
    DARK_GOLDENROD            = (184, 134, 11, 255)
    DARK_GRAY                 = (169, 169, 169, 255)
    DARK_GREEN                = (0, 100, 0, 255)
    DARK_KHAKI                = (189, 183, 107, 255)
    DARK_MAGENTA              = (139, 0, 139, 255)
    DARK_OLIVE_GREEN          = (85, 107, 47, 255)
    DARK_ORANGE               = (255, 140, 0, 255)
    DARK_ORCHID               = (153, 50, 204, 255)
    DARK_RED                  = (139, 0, 0, 255)
    DARK_SALMON               = (233, 150, 122, 255)
    DARK_SEA_GREEN            = (143, 188, 143, 255)
    DARK_SLATE_BLUE           = (72, 61, 139, 255)
    DARK_SLATE_GRAY           = (47, 79, 79, 255)
    DARK_TURQUOISE            = (0, 206, 209, 255)
    DARK_VIOLET               = (148, 0, 211, 255)
    DEEP_PINK                 = (255, 20, 147, 255)
    DEEP_SKY_BLUE             = (0, 191, 255, 255)
    DIM_GRAY                  = (105, 105, 105, 255)
    DODGER_BLUE               = (30, 144, 255, 255)
    FIREBRICK                 = (178, 34, 34, 255)
    FLORAL_WHITE              = (255, 250, 240, 255)
    FOREST_GREEN              = (34, 139, 34, 255)
    FUCHSIA                   = (255, 0, 255, 255)
    GAINSBORO                 = (220, 220, 220, 255)
    GHOST_WHITE               = (248, 248, 255, 255)
    GOLD                      = (255, 215, 0, 255)
    GOLDENROD                 = (218, 165, 32, 255)
    GRAY                      = (128, 128, 128, 255)
    GREEN                     = (0, 128, 0, 255)
    GREEN_YELLOW              = (173, 255, 47, 255)
    HONEYDEW                  = (240, 255, 240, 255)
    HOT_PINK                  = (255, 105, 180, 255)
    INDIAN_RED                = (205, 92, 92, 255)
    INDIGO                    = (75, 0, 130, 255)
    IVORY                     = (255, 255, 240, 255)
    KHAKI                     = (240, 230, 140, 255)
    LAVENDER                  = (230, 230, 250, 255)
    LAVENDER_BLUSH            = (255, 240, 245, 255)
    LAWN_GREEN                = (124, 252, 0, 255)
    LEMON_CHIFFON             = (255, 250, 205, 255)
    LIGHT_BLUE                = (173, 216, 230, 255)
    LIGHT_CORAL               = (240, 128, 128, 255)
    LIGHT_CYAN                = (224, 255, 255, 255)
    LIGHT_GOLDENROD_YELLOW    = (250, 250, 210, 255)
    LIGHT_GRAY                = (211, 211, 211, 255)
    LIGHT_GREEN               = (144, 238, 144, 255)
    LIGHT_PINK                = (255, 182, 193, 255)
    LIGHT_SALMON              = (255, 160, 122, 255)
    LIGHT_SEA_GREEN           = (32, 178, 170, 255)
    LIGHT_SKY_BLUE            = (135, 206, 250, 255)
    LIGHT_SLATE_GRAY          = (119, 136, 153, 255)
    LIGHT_STEEL_BLUE          = (176, 196, 222, 255)
    LIGHT_YELLOW              = (255, 255, 224, 255)
    LIME                      = (0, 255, 0, 255)
    LIME_GREEN                = (50, 205, 50, 255)
    LINEN                     = (250, 240, 230, 255)
    MAGENTA                   = (255, 0, 255, 255)
    MAROON                    = (128, 0, 0, 255)
    MEDIUM_AQUAMARINE         = (102, 205, 170, 255)
    MEDIUM_BLUE               = (0, 0, 205, 255)
    MEDIUM_ORCHID             = (186, 85, 211, 255)
    MEDIUM_PURPLE             = (147, 112, 219, 255)
    MEDIUM_SEA_GREEN          = (60, 179, 113, 255)
    MEDIUM_SLATE_BLUE         = (123, 104, 238, 255)
    MEDIUM_SPRING_GREEN       = (0, 250, 154, 255)
    MEDIUM_TURQUOISE          = (72, 209, 204, 255)
    MEDIUM_VIOLET_RED         = (199, 21, 133, 255)
    MIDNIGHT_BLUE             = (25, 25, 112, 255)
    MINT_CREAM                = (245, 255, 250, 255)
    MISTY_ROSE                = (255, 228, 225, 255)
    MOCCASIN                  = (255, 228, 181, 255)
    NAVAJO_WHITE              = (255, 222, 173, 255)
    NAVY                      = (0, 0, 128, 255)
    OLD_LACE                  = (253, 245, 230, 255)
    OLIVE                     = (128, 128, 0, 255)
    OLIVE_DRAB                = (107, 142, 35, 255)
    ORANGE                    = (255, 165, 0, 255)
    ORANGE_RED                = (255, 69, 0, 255)
    ORCHID                    = (218, 112, 214, 255)
    PALE_GOLDENROD            = (238, 232, 170, 255)
    PALE_GREEN                = (152, 251, 152, 255)
    PALE_TURQUOISE            = (175, 238, 238, 255)
    PALE_VIOLET_RED           = (219, 112, 147, 255)
    PAPAYA_WHIP               = (255, 239, 213, 255)
    PEACH_PUFF                = (255, 218, 185, 255)
    PERU                      = (205, 133, 63, 255)
    PINK                      = (255, 192, 203, 255)
    PLUM                      = (221, 160, 221, 255)
    POWDER_BLUE               = (176, 224, 230, 255)
    PURPLE                    = (128, 0, 128, 255)
    RED                       = (255, 0, 0, 255)
    ROSY_BROWN                = (188, 143, 143, 255)
    ROYAL_BLUE                = (65, 105, 225, 255)
    SADDLE_BROWN              = (139, 69, 19, 255)
    SALMON                    = (250, 128, 114, 255)
    SANDY_BROWN               = (244, 164, 96, 255)
    SEA_GREEN                 = (46, 139, 87, 255)
    SEASHELL                  = (255, 245, 238, 255)
    SIENNA                    = (160, 82, 45, 255)
    SILVER                    = (192, 192, 192, 255)
    SKY_BLUE                  = (135, 206, 235, 255)
    SLATE_BLUE                = (106, 90, 205, 255)
    SLATE_GRAY                = (112, 128, 144, 255)
    SNOW                      = (255, 250, 250, 255)
    SPRING_GREEN              = (0, 255, 127, 255)
    STEEL_BLUE                = (70, 130, 180, 255)
    TAN                       = (210, 180, 140, 255)
    TEAL                      = (0, 128, 128, 255)
    THISTLE                   = (216, 191, 216, 255)
    TOMATO                    = (255, 99, 71, 255)
    TURQUOISE                 = (64, 224, 208, 255)
    VIOLET                    = (238, 130, 238, 255)
    WHEAT                     = (245, 222, 179, 255)
    WHITE                     = (255, 255, 255, 255)
    WHITE_SMOKE               = (245, 245, 245, 255)
    YELLOW                    = (255, 255, 0, 255)
    YELLOW_GREEN              = (154, 205, 50, 255)
# endregion

# region: 程序定义颜色
    # 基础主题颜色
    PRIMARY                   = (13, 110, 253, 255)     # Bootstrap Primary Blue
    SECONDARY                 = (108, 117, 125, 255)    # Bootstrap Secondary Gray
    SUCCESS                   = (25, 135, 84, 255)      # Bootstrap Success Green
    DANGER                    = (220, 53, 69, 255)      # Bootstrap Danger Red
    WARNING                   = (255, 193, 7, 255)      # Bootstrap Warning Yellow
    INFO                      = (13, 202, 240, 255)     # Bootstrap Info Cyan
    LIGHT                     = (248, 249, 250, 255)    # Bootstrap Light Gray
    DARK                      = (33, 37, 41, 255)       # Bootstrap Dark Gray

    # 背景颜色
    BACKGROUND                = (33, 37, 41, 255)       # Dark mode background
    BACKGROUND_SECONDARY      = (52, 58, 64, 255)       # Dark mode secondary background
    BACKGROUND_ELEVATED       = (52, 58, 64, 255)       # Elevated surface background

    # 文本颜色
    TEXT                      = (255, 255, 255, 255)    # Primary text color
    TEXT_MUTED                = (173, 181, 189, 255)    # Muted text color
    TEXT_SECONDARY            = (108, 117, 125, 255)    # Secondary text color
    TEXT_DISABLED             = (73, 80, 87, 255)       # Disabled text color

    # 主题文本颜色
    TEXT_PRIMARY              = (102, 163, 255, 255)    # Primary text emphasis
    TEXT_SUCCESS              = (64, 201, 128, 255)     # Success text emphasis
    TEXT_DANGER               = (255, 102, 102, 255)    # Danger text emphasis
    TEXT_WARNING              = (255, 184, 77, 255)     # Warning text emphasis
    TEXT_INFO                 = (64, 201, 201, 255)     # Info text emphasis
    TEXT_LIGHT                = (248, 249, 250, 255)    # Light text color
    TEXT_DARK                 = (173, 181, 189, 255)    # Dark text color

    # 背景强调颜色 (bg-subtle)
    BG_PRIMARY_SUBTLE         = (2, 27, 58, 255)        # Primary background subtle
    BG_SECONDARY_SUBTLE       = (24, 26, 27, 255)       # Secondary background subtle
    BG_SUCCESS_SUBTLE         = (5, 30, 15, 255)        # Success background subtle
    BG_DANGER_SUBTLE          = (30, 5, 5, 255)         # Danger background subtle
    BG_WARNING_SUBTLE         = (30, 20, 5, 255)        # Warning background subtle
    BG_INFO_SUBTLE            = (5, 30, 30, 255)        # Info background subtle
    BG_LIGHT_SUBTLE           = (33, 37, 41, 255)       # Light background subtle
    BG_DARK_SUBTLE            = (52, 58, 64, 255)       # Dark background subtle

    # 边框颜色
    BORDER                    = (73, 80, 87, 255)       # Default border color
    BORDER_SECONDARY          = (52, 58, 64, 255)       # Secondary border color
    BORDER_PRIMARY            = (13, 110, 253, 255)     # Primary border color
    BORDER_SUCCESS            = (25, 135, 84, 255)      # Success border color
    BORDER_DANGER             = (220, 53, 69, 255)      # Danger border color
    BORDER_WARNING            = (255, 193, 7, 255)      # Warning border color
    BORDER_INFO               = (13, 202, 240, 255)     # Info border color

    # 边框强调颜色 (border-subtle)
    BORDER_PRIMARY_SUBTLE     = (2, 27, 58, 255)        # Primary border subtle
    BORDER_SECONDARY_SUBTLE   = (24, 26, 27, 255)       # Secondary border subtle
    BORDER_SUCCESS_SUBTLE     = (5, 30, 15, 255)        # Success border subtle
    BORDER_DANGER_SUBTLE      = (30, 5, 5, 255)         # Danger border subtle
    BORDER_WARNING_SUBTLE     = (30, 20, 5, 255)        # Warning border subtle
    BORDER_INFO_SUBTLE        = (5, 30, 30, 255)        # Info border subtle

    # 链接颜色
    LINK                      = (102, 163, 255, 255)    # Link color
    LINK_HOVER                = (128, 179, 255, 255)    # Link hover color
    LINK_VISITED              = (179, 128, 255, 255)    # Link visited color

    # 输入框颜色
    INPUT_BACKGROUND          = (52, 58, 64, 255)       # Input background
    INPUT_BORDER              = (73, 80, 87, 255)       # Input border
    INPUT_FOCUS_BORDER        = (13, 110, 253, 255)     # Input focus border
    INPUT_DISABLED_BACKGROUND = (33, 37, 41, 255)       # Input disabled background
    INPUT_DISABLED_TEXT       = (108, 117, 125, 255)    # Input disabled text

    # 阴影颜色
    SHADOW                    = (0, 0, 0, 255)          # Shadow color (black with opacity)
    SHADOW_SM                 = (0, 0, 0, 255)          # Small shadow
    SHADOW_MD                 = (0, 0, 0, 255)          # Medium shadow
    SHADOW_LG                 = (0, 0, 0, 255)          # Large shadow


# region: 操作方法
    @staticmethod
    def dim(
        color: tuple[int, int, int, int],
        factor: float,
    ) -> tuple[int, int, int, int]:
        """
        将颜色变暗

        Args:
            color (PgColor): 颜色
            factor (float): 变暗因子, 范围: 0.0 - 1.0, 0.0 表示不变, 1.0 表示完全变暗

        Returns:
            tuple[int, int, int, int]: 变暗后的颜色
        """
        assert 0.0 <= factor <= 1.0, "Factor must be between 0.0 and 1.0"
        factor = 1.0 - factor
        
        r = int(color[0] * factor)
        g = int(color[1] * factor)
        b = int(color[2] * factor)
        
        return r, g, b, color[3]

    @staticmethod
    def alpha(
        color: tuple[int, int, int, int],
        factor: float,
    ) -> tuple[int, int, int, int]:
        """
        调整颜色透明度

        Args:
            color (tuple[int, int, int, int]): 颜色
            factor (float): 透明度因子, 范围: 0.0 - 1.0, 0.0 表示不变, 1.0 表示完全透明

        Returns:
            tuple[int, int, int, int]: 调整透明度后的颜色
        """
        assert 0.0 <= factor <= 1.0, "Factor must be between 0.0 and 1.0"
        factor = 1.0 - factor

        alpha = int(color[3] * factor)
        alpha = min(max(alpha, 0), 255)
        return color[0], color[1], color[2], alpha