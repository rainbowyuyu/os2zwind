# zwind 封装说明（把 `import opensees as ops` 改成 `import zwind as ops`）

## 你能做什么

当你已经有 `bin/opensees.pyd` 后，你可以在代码里把：

```python
import opensees as ops
```

改成：

```python
import zwind as ops
```

然后继续用原来的 OpenSeesPy API（`wipe / model / node / element / analyze` 等不用改）。

> 说明：`zwind` 只是一个轻量的 Python 封装层，不会去重命名/替换你的二进制扩展。

## 本次相关文件

1. 封装入口：[`zwind/__init__.py`](zwind/__init__.py)
2. 示例脚本：[`EXAMPLES/ExamplePython/zwind_import_example.py`](EXAMPLES/ExamplePython/zwind_import_example.py)
3. 底层扩展产物：[`bin/opensees.pyd`](bin/opensees.pyd)（需要你自己编译生成/放到这里）

## 从 git 下载后如何直接用

前提：你的工程根目录里已有 `bin/opensees.pyd`。

1. 运行示例（建议用和编译 `opensees.pyd` 一致的 Python，当前你构建的是 Python 3.14）

```powershell
& "C:\Users\zju\AppData\Local\Programs\Python\Python314\python.exe" `
  EXAMPLES\ExamplePython\zwind_import_example.py
```

成功输出类似：

```text
analyze ok: 0 time: 1.0
```

2. 改你的代码

把 `import opensees as ops` 换成 `import zwind as ops`，其它不用动。


