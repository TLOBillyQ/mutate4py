# mutate4py

> 「4py 系列」:[crap4py](http://lzxsvn:3000/qinyuanj/crap4py) · [dry4py](http://lzxsvn:3000/qinyuanj/dry4py) · [mutate4py](http://lzxsvn:3000/qinyuanj/mutate4py)
> 对应「4lua 系列」:[mutate4lua](http://lzxsvn:3000/eggy/mutate4lua)

`mutate4py` 是 Differential mutation testing for Python (manifest footer)。它是「4lua 系列」的 Python 同构实现:
上游 unclebob 的 mutate4clj/go/java 规格以 Python 忠实实现(「零本地独有发明」教义;
Python 无上游规格的部分以本文档为规格,对齐不变量逐条列出,偏离注明理由)。

库自包含:`src/mutate4py/` 下不硬编码任何宿主专属路径;共享基础件
(common / covdata / astnorm)vendor 在 `_internal/`,不是公共 API。
源自 [ugc-image-tool](http://lzxsvn:3000/qinyuanj/ugc-image-tool) 的 `tools/packages/mutate`。

## 安装与入口

```sh
pip install git+http://lzxsvn:3000/qinyuanj/mutate4py.git
python -m mutate4py --help        # 或直接 mutate4py --help
```

在宿主项目根目录运行;宿主解释器优先取 `.venv/bin/python`,否则当前解释器。
覆盖率只来自宿主的 coverage.py 产物(`coverage json`),宿主需装 `coverage`。

## mutate(对齐不变量)

- 退出码 `0` 成功 / `1` 用法错误 / `2` baseline 失败 / `3` 存在存活 mutant。
- manifest 以 `# mutate4py-manifest` 注释块形式嵌入目标文件尾部(外部
  `.mutate4py/manifest/` 存储已废除);manifest 只在干净运行后写入。
- 差异化选择:无 manifest → 所有已覆盖位点;模块 hash 未变 → 0 个位点;
  hash 变化 → 仅变动的 scope。
- 变异集合:布尔翻转、比较/算术运算符交换、`and` ↔ `or`、一元 `not`/`-` 移除、
  `0` ↔ `1`、赋值右值 → `None`。
- scope 身份以声明为基准(模块级函数与类方法);worker 操作项目副本,
  原始文件永不在原地变异;超时视为已击杀。
- 测试经项目 pytest 运行(上游「内置构建工具调用」的 Python 对应);
  `--test-command` 为同款逃生舱(禁用覆盖率过滤)。
- footer 识别:marker 必须**独占一行**且其后一直到文件末尾只剩注释/空行;文档或
  字符串里引用的 marker 不会被当成 footer,源文件也不会被 strip 截断。
- manifest 登记范围诚实:只有「位点全部跑完」「无位点」「整体未触及且旧记录语义哈希
  一致」三类 scope 才写回;被 `--lines`/覆盖率过滤切走的位点不会被一次局部运行
  记成「已验证」(全量登记只由 `--update-manifest` 做)。
- 判定可信的三个前提(每个位点都在项目副本里跑):副本**租约**(同一副本同一时刻
  只跑一个位点;按「位点序号 % worker 数」分副本会互相改写同一文件)、写变异文件前
  清掉目标包目录的 `__pycache__`(.pyc 按「整秒 mtime + 字节数」判鲜,同尺寸 mutant
  会被旧字节码顶替)、worker **私有 `TMPDIR/TEMP/TMP`**(并发 pytest 在同一条系统临时
  目录上会串台,读到别人的 `tmp_path`)。
- scope 语义哈希 = 归一化 AST 序列化结果的 FNV-1a(格式无关)。**掩蔽口径**:归一化
  把标识符归为 `ident`、字面量归为 `literal/<kind>`,所以纯改名与纯改字面量取值的
  编辑不会被差分感知(有测试钉死这条口径;要换口径是设计变更,见「已知问题」)。
- 覆盖率取数口径固定 `--source=src`(与 crap/verify 同一份 `covdata` 流水线):目标
  在 `tools/` 下时产物里没有它的条目,自动退化为「不过滤,全部位点都跑」。跑工具链
  自身时用逃生舱:`--test-command "$PWD/.venv/bin/python -m pytest tests/test_tools_*.py -x -q"`
  (单位点约 1 s;默认路径每次都要付一整遍覆盖率流水线 ~28 s)。
- `--test-command` 交给 `/bin/sh -c`,必须是**单条简单命令**:多语句命令(`a; b`)
  超时时只有 `sh` 被 kill,pytest 孙进程会成为孤儿。
- 覆盖率来源仅限 coverage.py 产物(`coverage json`)。

```sh
python tools/cli.py mutate <file.py> [--scan|--update-manifest|--since-last-run|
    --lines N,N|--mutate-all|--reuse-coverage|--max-workers N|--timeout-factor N|
    --test-command CMD|--mutation-warning N|--verbose]
```

**有意偏离**:scope 收集只含模块级函数与类方法(lua 版连匿名/嵌套函数一起收集);
构造性等价变异抑制链按位点 kind 查谓词表(可扩展,表内顺序固定便于评审):boolop
要求操作数**完整 AST 逐字相同**(不能用语义哈希比较——它掩蔽标识符,会把
`a and b` 误判成同操作数而丢掉一条真实变异)、`+/-` 含常量 `0` 操作数、`rhs->none`
右值已是 `None` 字面量;`--reuse-coverage` 复用按项目哈希判鲜的缓存
(lua 版复用归因矩阵缓存)。

## 布局

```text
src/mutate4py/
  cli.py          # 选项走查与退出码
  engine.py       # 核心算法
  manifest.py     # manifest footer 读写
  _internal/      # vendor 的共享基础件:common / covdata / astnorm
tests/            # pytest;test_internal_* 覆盖 _internal
```

## 测试

```sh
python3 -m venv .venv && .venv/bin/pip install -e '.[test]'
.venv/bin/python -m pytest
```
