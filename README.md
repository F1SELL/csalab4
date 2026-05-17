# Лабораторная работа №4

- ФИО: Фадин Константин Алексеевич
- Группа: P3209
- Вариант: `lisp | acc | neum | mc | tick | binary | stream | port | pstr | prob1 | superscalar`

## Язык программирования

### Синтаксис (EBNF)

```ebnf
program        = { form } ;
form           = atom | list | block ;
list           = "(" , { form } , ")" ;
block          = "{" , { form } , "}" ;

atom           = integer | symbol | string ;
integer        = ["-"] , digit , { digit } ;
symbol         = letter , { letter | digit | "_" | "-" | "?" | "!" } ;
string         = '"' , { char } , '"' ;

expr           = integer
               | symbol
               | string
               | ( "begin" | "progn" | "block" ) , { expr }
               | ( "setq" | "assign" | "set" ) , symbol , expr
               | ( "if" | "check" ) , expr , expr , [ expr ]
               | ( "loop" , expr , expr )
               | ( "repeat" , expr )
               | ( "+" | "-" | "*" | "/" | "%" ) , expr , expr , { expr }
               | ( "=" | "!=" | ">" | "<" | ">=" | "<=" ) , expr , expr
               | ( "in" , integer )
               | ( "out" , integer , expr )
               | ( "print" , expr )
               | call ;

call           = "(" , symbol , { expr } , ")" ;

func_def       = "(" , ("defun" | "func") , symbol , "(" , { symbol } , ")" , { expr } , ")" ;
```

Комментарий: символ `;` начинает комментарий до конца строки.

### Семантика

- Стратегия вычислений: строгая, слева направо.
- Область видимости: лексическая в теле функции; доступ к глобальным слотам по имени.
- Любая форма — выражение: результат остаётся в `ACC`.
- Типизация: динамическая; основной тип — целое 32‑битное слово, строки — `pstr` (len + chars).
- Вызовы функций: аргументы вычисляются, кладутся в стек вызова, затем `CALL`.
- Ввод/вывод: `(in port)` читает токен из потока, `(out port expr)` пишет символ.
- Строки: литералы компилируются в `pstr` в секции данных; `print` печатает строку посимвольно.

## Организация памяти

- Архитектура `neum`: единая однопортовая память для кода и данных.
- Размер машинного слова: 32 бит.
- Адресация: непосредственная (`LOADI`), прямая по адресу (операнд 24‑бит).

```text
Registers
+------------------+
| ACC, SHADOW, PC  |
| IR, MAR, FLAGS   |
+------------------+

Unified Memory (single-port, neum)
+------------------------------+
| 0x0000: code[0]              |
|   ...                        |
| 0x00FF: code[N]              |
| 0x0100: const pool / globals |
|   ...                        |
| 0x0200: pstr literals         |
|   len, chars...               |
| 0x0300: temp slots (__tmp*)   |
|   ...                        |
+------------------------------+
```

Правила размещения:
- Код идёт подряд с адреса 0.
- Глобальные переменные/константы/временные слоты — в data‑сегменте.
- Строки `pstr` записываются как длина + последовательность кодов символов.

## Система команд

### Особенности

- Архитектура `acc`: вычисления идут через `ACC`.
- Ввод‑вывод — port‑mapped (`IN`/`OUT`).
- Микрокод: базовый цикл `FETCH -> DECODE -> EXEC`.
- Tick‑модель: одна микрооперация = один тик.

### Формат машинного слова

- 32 бит: `[ opcode:8 | arg:24 ]`.
- Порядок байт в файле: big‑endian.
- Пример листинга: `<addr> - <HEX> - <mnemonic>`.

### Таблица инструкций (базовый скалярный цикл)

Базовая стоимость: `FETCH + DECODE + EXEC = 3 тика` на инструкцию. В superscalar‑режиме возможны пары инструкций в одном слоте.

| Инструкция | Арг | Описание |
|---|---:|---|
| `NOP` | — | пустая операция |
| `HALT` | — | останов |
| `LOADI` | imm | `ACC <- imm` |
| `LOAD` | addr | `ACC <- MEM[addr]` |
| `STORE` | addr | deferred‑store через `SHADOW` |
| `ADD/SUB/MUL/DIV/MOD` | addr | арифметика `ACC` с `MEM[addr]` |
| `CMP` | addr | сравнение, флаги `Z/L/G`, результат в `ACC` |
| `JMP/JZ/JNZ/JL/JG` | addr | переход |
| `IN` | port | `ACC <- input(port)` |
| `OUT` | port | `output(port) <- ACC` |
| `SWAP` | — | `ACC <-> SHADOW` |
| `STORE_SHADOW` | addr | `MEM[addr] <- SHADOW` |
| `CALL/RET` | addr/— | вызов/возврат |
| `PUSH/POP` | —/addr | кадры вызовов |
| `LOAD_LOCAL/STORE_LOCAL` | slot | локальные слоты |

## Транслятор

CLI:

```bash
python3 translator.py <input.lisp> <output.bin>
```

Этапы:
- лексер → парсер (AST);
- компиляция AST в код/данные;
- запись артефактов.

Артефакты:
- `output.bin` — бинарный код;
- `output.bin.hex` — листинг;
- `output.bin.data.json` — данные и метки;
- `output.bin.ast.json` — AST (машинный формат);
- `output.bin.ast.txt` — AST в читаемом S-exp виде.

## Модель процессора

CLI:

```bash
python3 machine.py <code.bin> <input.txt>
```

Ввод/вывод:
- вход — поток токенов (символы);
- выход — поток символов в буфер порта `1`.

Лог содержит:
- микроуровень (`MICRO uPC=...`),
- исполнение инструкций (`EXEC ...`),
- события superscalar (`SUPER issue2/...`).

**Материалы для защиты:** пошаговый разбор всех файлов, решений и **каждой команды ISA** — [docs/polnoye_rukovodstvo_zaschita.md](docs/polnoye_rukovodstvo_zaschita.md); чтение ASCII-схем — [docs/skhemy_dlya_zaschity.md](docs/skhemy_dlya_zaschity.md).

### DataPath

Схема отражает **аппаратную** структуру (мультиплексоры, защёлки, один порт к данным), а не классы Python. Пошагово «как читать рисунок» и связь с симулятором: [docs/skhemy_dlya_zaschity.md](docs/skhemy_dlya_zaschity.md).

```text
  Neumann: одно адресное пространство; один физический порт к словам данных
  (команды в образе .bin лежат в том же космосе адресов, что и переменные).

                              +------------------------------+
                              |  Data memory (single-port)   |
                              |  слова данных по адресу MAR |
      mem_addr  -------------->| addr                         |
      mem_rd    -------------->| rd                           |---- mem_data_out
      mem_wr    -------------->| wr                           |
      mem_data_in ------------>| data_in                      |
                              +------------------------------+

  Выборка команды: PC -> образ команд (в модели: массив `code[]`; по смыслу
  чтение из code-сегмента объединённой памяти) -> IR.

             +-----------+                             +-------------------+
             |   IR      |<---- ir_we -----------------| InstrFetch(PC)    |
             +-----------+                             +-------------------+
                   |
                   v
            +---------------+                  +--------------------+
            |  opcode/arg   |---opcode-------->| µDecoder / µROM    |
            +---------------+                  | (см. схему CU ниже)|
                                               +--------------------+
                                                          |
                        «шина управления» (обобщённо,     v
                         не каждая линия)           pc_we, mem_*, acc_we, ...

     +-----+   +---------+   +-------------------+     +-------------------+
     | PC  |-->| PC MUX  |-->| MAR (защёлка адреса данных) -> mem_addr     |
     +-----+   +---------+   +-------------------+
       ^  |        ^
       |  +-- pc+1 |
       |           +-- branch_target(IR.arg)
       +------------------ pc_we ----------------------------------

     +------+        +------+        +---------------------------+
     | ACC  |------->|      |------->| FLAGS (Z/L/G)             |
     +------+        | ALU  |        | flag_we                   |
       ^             |      |        +---------------------------+
       |             +------+                 ^
       |                ^                     |
       |                |                     |
       |         +--------------+             |
       |         | ALU_B MUX    |<-- mem_data_out / imm / shadow
       |         +--------------+
       |                ^
     acc_we             |
       |             +--------+
       +-------------| SHADOW |
                     +--------+
                         ^
                         |
                    shadow_we / swap

     +------------------+                      +------------------+
     | PORT_IN (id=0)   |---- in_we ---------> | ACC write path   |
     +------------------+                      +------------------+
     +------------------+                      +------------------+
     | PORT_OUT (id=1)  |<--- out_we --------- | ACC low byte     |
     +------------------+                      +------------------+
```

### ControlUnit (microcoded + superscalar)

Схема CU **не дублирует** все провода к каждому элементу DP: блок «Datapath control» — обозначение **группы** сигналов (как в методичке). Подробнее: [docs/skhemy_dlya_zaschity.md](docs/skhemy_dlya_zaschity.md).

```text
                       +-----------------------+
                       |         µPC           |
                       +-----------------------+
                             |          ^
                             |          | µpc_we / µpc_sel
                             v          |
                       +-----------------------+
                       |    Microcode ROM      |
                       | (отдельная память     |
                       |  микропрограмм)       |
                       +-----------------------+
                             |  \
              control_word --+   \-- next µaddr / dispatch fields
                             v
   +-------------------------------------------------------------------+
   | К регистрам DP (обобщённо): pc_we ir_we mar_we acc_we shadow_we   |
   | mem_rd mem_wr in_we out_we ...                                    |
   +-------------------------------------------------------------------+

   +----------------------+             +---------------------------+
   | Instruction Decoder  |<--- IR ---- | opcode / класс ветвления |
   +----------------------+             +---------------------------+
             |                                      |
             +---------- dispatch table ------------+

   +----------------------+      flags/scoreboard    +----------------------+
   | Hazard/Dependency    |<------------------------ | ACC/SHADOW tags       |
   | check (RAW/WAR/WAW)  | -----------------------> | stall / scalar fallback|
   +----------------------+                           +----------------------+

   +----------------------+       issue2_en
   | Dual-issue selector  | ---------------------> {ALU op + MEM/STORE}
   | (superscalar window) |
   +----------------------+
```

## Микрокод

Отдельная память микропрограмм — модуль [`microcode/micro_rom.py`](microcode/micro_rom.py):

- `MROM[]` — массив control words (`encode_signals`);
- `MROM_DESC[]` — текст для журнала (`uPC=N ...`);
- `DECODER[opcode]` — адрес микропрограммы исполнения.

**FETCH = 2 микрошага (2 тика):** uPC 0 — `IR <- Mem[PC]`; uPC 1 — `uPC <- DECODER[opcode]`. Далее одна микрокоманда `EXEC <opcode>` (1 тик), затем снова FETCH. Итого **3 тика** на простую инструкцию в скалярном режиме.

Справочное описание: [`microcode/micro_rom.json`](microcode/micro_rom.json).

## Superscalar: эффект и проверка

Политика:
- допустимая пара: `ALU + MEMIO`;
- проверки зависимостей: `RAW/WAR/WAW`;
- события фиксируются в логе: `SUPER issue2`, `SUPER stall`, `SUPER commit2`.

Как сравнить тики:

```bash
# superscalar включён (по умолчанию)
python3 machine.py out/program.bin input.txt

# superscalar выключён (скалярный режим)
SUPERSCALAR=0 python3 machine.py out/program.bin input.txt
```

Сравните поле `ticks` в конце вывода.

Пример (микропрограмма из `tests/test_first5.py`, dual-issue на паре `ADD` + `STORE_SHADOW`): при одинаковом результате на выходе суперскалярный режим даёт меньше тиков симуляции, чем скалярный (значения снимаются автотестом `test_superscalar_fewer_ticks_than_scalar`):

| Режим | Тики (пример) |
|------|----------------|
| `SUPERSCALAR=1` (по умолчанию) | 15 |
| `SUPERSCALAR=0` | 19 |

## Тестирование

Всего **12** интеграционных/регрессионных тестов (`pytest`):

- [`tests/test_golden.py`](tests/test_golden.py) — golden‑pipeline: `hello`, `cat`, `hello_user_name`, `sort`, `double_precision`, `prob1`, **`fact`** (рекурсия);
- [`tests/test_first5.py`](tests/test_first5.py) — AST/алиасы, трассировка микрокода, superscalar issue/stall, **`(print (setq …))` как выражение**, сравнение тиков SS vs scalar.

Golden-тесты сравнивают **полный журнал** (`golden/<name>.log.txt`), **pretty AST** (`golden/<name>.ast.txt`), вывод и `expected_ticks`.

Перегенерация эталонов после изменения модели:

```bash
python3 scripts/regenerate_golden.py
```

Пример запуска:

```bash
python3 -m pytest -q
python3 machine.py out/program.bin input.txt --log-file run.log.txt
```
