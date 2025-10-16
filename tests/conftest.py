"""pytest共通設定."""

import warnings

warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module=r"websockets\.legacy(\..*)?",
)
