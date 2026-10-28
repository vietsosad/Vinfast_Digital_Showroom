from __future__ import annotations

import logging
from pathlib import Path, PurePosixPath

logger = logging.getLogger(__name__)


class LocalFileStorage:
    """Adapter lưu tệp trên máy chủ và trả URL tương đối dưới đường dẫn /static.

    Khi được dùng trong ứng dụng, ``root`` cần trỏ tới đúng thư mục mà FastAPI
    mount để phục vụ tệp tĩnh; ví dụ ``static/`` tương ứng với URL ``/static``.
    """

    def __init__(self, root: Path, public_prefix: str = "/static"):
        # Lưu đường dẫn tuyệt đối đã chuẩn hóa để kiểm tra mọi tệp nằm trong root.
        self.root = root.resolve()
        # Bỏ dấu / cuối để khi ghép URL không tạo ra dấu gạch chéo kép.
        self.public_prefix = public_prefix.rstrip("/")

    def save(self, folder: str, filename: str, content: bytes) -> str:
        # PurePosixPath giữ URL dùng dấu / trên mọi hệ điều hành; đường dẫn đĩa
        # thực tế sẽ được chuyển sang kiểu Path trong _resolve.
        relative = PurePosixPath(folder) / filename
        target = self._resolve(relative)
        # Tạo các thư mục con (ví dụ uploads/cars) nếu chúng chưa tồn tại.
        target.parent.mkdir(parents=True, exist_ok=True)
        # Lỗi tạo thư mục/ghi tệp được để truyền về bên gọi, không giả vờ thành công.
        target.write_bytes(content)
        # Chỉ lưu URL trong database; nội dung tệp vẫn nằm dưới root trên đĩa.
        return f"{self.public_prefix}/{relative.as_posix()}"

    def delete(self, url: str) -> None:
        # Không xóa URL ngoài namespace do adapter này quản lý (ví dụ URL bên ngoài).
        if not url.startswith(f"{self.public_prefix}/"):
            return
        try:
            # Bỏ prefix công khai, kiểm tra lại đường dẫn rồi xóa; tệp không tồn tại
            # được xem là đã xóa để thao tác dọn dẹp có thể gọi lặp an toàn.
            self._resolve(PurePosixPath(url.removeprefix(f"{self.public_prefix}/"))).unlink(missing_ok=True)
        except (OSError, ValueError):
            # Lỗi I/O hoặc đường dẫn không hợp lệ không làm gián đoạn luồng dọn dẹp,
            # nhưng vẫn được ghi log để có thể điều tra.
            logger.warning("Could not remove stored file %s", url, exc_info=True)

    def _resolve(self, relative: PurePosixPath) -> Path:
        # resolve() chuẩn hóa cả .. và liên kết tượng trưng; chỉ chấp nhận kết quả
        # thực sự nằm bên trong root để ngăn đường dẫn thoát khỏi thư mục lưu.
        target = (self.root / Path(*relative.parts)).resolve()
        if self.root not in target.parents:
            raise ValueError("Storage path escapes the static directory")
        return target
