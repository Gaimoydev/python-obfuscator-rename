import ast, re, random, io, tokenize, os, sys, platform, math
import argparse

def red(text): return f"\033[91m{text}\033[0m"
def blue(text): return f"\033[94m{text}\033[0m"
def water(text): return f"\033[96m{text}\033[0m"
def purple(text): return f"\033[95m{text}\033[0m"

def remove_docs_node(node):
    if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)) and ast.get_docstring(node):
        node.body = node.body[1:]
    for child in ast.iter_child_nodes(node):
        remove_docs_node(child)

def remove_docs(source):
    io_obj = io.StringIO(source)
    out = ""
    prev_toktype = tokenize.INDENT
    last_lineno = -1
    last_col = 0
    for tok in tokenize.generate_tokens(io_obj.readline):
        token_type = tok[0]
        token_string = tok[1]
        start_line, start_col = tok[2]
        end_line, end_col = tok[3]
        if start_line > last_lineno:
            last_col = 0
        if start_col > last_col:
            out += (" " * (start_col - last_col))
        if token_type == tokenize.COMMENT:
            pass
        elif token_type == tokenize.STRING:
            if prev_toktype != tokenize.INDENT:
                if prev_toktype != tokenize.NEWLINE:
                    if start_col > 0:
                        out += token_string
        else:
            out += token_string
        prev_toktype = token_type
        last_col = end_col
        last_lineno = end_line
    out = '\n'.join(l for l in out.splitlines() if l.strip())
    return out

def do_rename(pairs, code):
    for key in pairs:
        code = re.sub(fr"\b({key})\b", pairs[key], code, re.MULTILINE)
    return code

def random_name(prefix, length, charset):
    return prefix + ''.join(random.choice(charset) for _ in range(length))

def rename(parsed, prefix, length, charset, do_not_rename, code=""):
    funcs = {
        node for node in ast.walk(parsed) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    classes = {
        node for node in ast.walk(parsed) if isinstance(node, ast.ClassDef)
    }
    args = {
        node.id for node in ast.walk(parsed) if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Load)
    }
    attrs = {
        node.attr for node in ast.walk(parsed) if isinstance(node, ast.Attribute) and not isinstance(node.ctx, ast.Load)
    }
    for func in funcs:
        if func.args.args:
            for arg in func.args.args:
                args.add(arg.arg)
        if func.args.kwonlyargs:
            for arg in func.args.kwonlyargs:
                args.add(arg.arg)
        if func.args.vararg:
            args.add(func.args.vararg.arg)
        if func.args.kwarg:
            args.add(func.args.kwarg.arg)

    pairs = {}
    used = set()
    for func in funcs:
        if func.name == "__init__":
            continue
        if func.name in do_not_rename:
            continue
        newname = random_name(prefix, length, charset)
        while newname in used:
            newname = random_name(prefix, length, charset)
        used.add(newname)
        pairs[func.name] = newname

    for _class in classes:
        if _class.name in do_not_rename:
            continue
        newname = random_name(prefix, length, charset)
        while newname in used:
            newname = random_name(prefix, length, charset)
        used.add(newname)
        pairs[_class.name] = newname

    for arg in args:
        if arg in do_not_rename or arg == 'f' or arg == 'r':
            continue
        newname = random_name(prefix, length, charset)
        while newname in used:
            newname = random_name(prefix, length, charset)
        used.add(newname)
        pairs[arg] = newname

    for attr in attrs:
        if attr in do_not_rename:
            continue
        newname = random_name(prefix, length, charset)
        while newname in used:
            newname = random_name(prefix, length, charset)
        used.add(newname)
        pairs[attr] = newname

    string_regex = r"('|\")[\x1f-\x7e]{1,}?('|\")"

    original_strings = re.finditer(string_regex, code, re.MULTILINE)
    originals = []

    for matchNum, match in enumerate(original_strings, start=1):
        originals.append(match.group().replace("\\", "\\\\"))

    placeholder = os.urandom(16).hex()
    code = re.sub(string_regex, f"'{placeholder}'", code, 0, re.MULTILINE)

    for i in range(len(originals)):
        for key in pairs:
            originals[i] = re.sub(r"({.*)(" + key + r")(.*})", "\\1" + pairs[key] + "\\3", originals[i], re.MULTILINE)

    while True:
        found = False
        code = do_rename(pairs, code)
        for key in pairs:
            if re.findall(fr"\b({key})\b", code):
                found = True
        if not found:
            break

    replace_placeholder = r"('|\")" + placeholder + r"('|\")"
    for original in originals:
        code = re.sub(replace_placeholder, original, code, 1, re.MULTILINE)

    return code

def obfuscate_code(file_path, prefix, length, charset, removedocs, do_not_rename):
    with open(file_path, 'r', encoding='utf-8') as f:
        source_code = f.read()
    tree = ast.parse(source_code)
    remove_docs_node(tree)
    obfuscated_code = rename(tree, prefix, length, charset, do_not_rename, source_code)
    if removedocs == "True":
        obfuscated_code = remove_docs(obfuscated_code)
    output_file = file_path.replace('.py', '-obf.py')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(obfuscated_code)
    print(water(f"[+] Successfully Rename: {output_file}"))

def obfuscate_code_for_folder(folder_path, prefix, length, charset, removedocs, do_not_rename):
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                print(water(f"[+] Processing file: {file_path}"))
                obfuscate_code(file_path, prefix, length, charset, removedocs, do_not_rename)

def main():
    parser = argparse.ArgumentParser(description="pnic-obf")
    parser.add_argument("--i", required=True, help="input python file or folder")
    parser.add_argument("--prefix", default="_", help="name prefix(_ = _0xd)")
    parser.add_argument("--length", type=int, default=8, help="name length(8)")
    parser.add_argument("--charset", default="ᕾᕸᖙ", help="name charset(il, o0, ᕾᕸᖙ, 髢ｫ)")
    parser.add_argument("--removedocs", default="True", help="remove docs(#hello world)")
    parser.add_argument("--norename", default="", help="comma-separated list of names not to rename (os,sys,io)")
    args = parser.parse_args()

    if not os.path.exists(args.i):
        print(red(f"[!] Error: {args.i} Not Exist"))
        sys.exit(1)

    do_not_rename = set(args.norename.split(",")) if args.norename else set()

    if os.path.isdir(args.i):
        obfuscate_code_for_folder(args.i, args.prefix, args.length, args.charset, args.removedocs, do_not_rename)
    else:
        obfuscate_code(args.i, args.prefix, args.length, args.charset, args.removedocs, do_not_rename)

if __name__ == "__main__":
    main()
