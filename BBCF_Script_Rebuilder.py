import os, struct, astor, sys
from ast import *
from BBCF_Script_Parser import upon_db, slot_db, command_db, move_inputs, normal_inputs

command_db_lookup = {}
slot_db_lookup = {}
named_value_lookup = {}
named_button_lookup = {}
named_direction_lookup = {}
upon_db_lookup = {}

for k, v in command_db.items():
    v["id"] = k
    if "name" in v:
        v["name"] = v["name"].lower()
        command_db_lookup[v["name"]] = v
    else:
        command_db_lookup["unknown" + k] = v
slot_db_lookup = {v.lower(): k for k, v in slot_db.items()}
for k, v in move_inputs.items():
    named_value_lookup[v.lower()] = k
for k, v in normal_inputs['grouped_values'].items():
    named_value_lookup[v.lower()] = k
for k, v in normal_inputs['button_byte'].items():
    named_button_lookup[v.lower()] = k
for k, v in normal_inputs['direction_byte'].items():
    named_direction_lookup[v.lower()] = k
upon_db_lookup = {v.lower(): k for k, v in upon_db.items()}

MODE = "<"
GAME = "bb"
binary_output = ""


def decode_upon(s):
    s = s.lower()
    if s.replace("upon_", "") in upon_db_lookup:
        return int(upon_db_lookup[s.replace("upon_", "")])
    else:
        return int(s.replace("upon_", ""))


def decode_var(node):
    if isinstance(node, UnaryOp):
        return [0, -node.operand.value]
    elif isinstance(node, Constant):
        return [0, node.value]
    elif node.id.lower().replace("slot_", "") in slot_db_lookup:
        return [2, int(slot_db_lookup[node.id.lower().replace("slot_", "")])]
    else:
        return [2, int(node.id.lower().replace("slot_", ""))]


def write_command_by_name(name, params):
    cmdData = command_db_lookup[name.lower()]
    write_command_by_id(cmdData["id"], params)


def write_command_by_id(id, params):
    global binary_output
    cmd_data = command_db[id]
    my_params = list(params)
    for index, oValue in enumerate(my_params):
        if isinstance(oValue, str):
            pass
        elif isinstance(oValue, int):
            pass
        elif isinstance(oValue, float):
            pass
        elif isinstance(oValue, Constant):
            my_params[index] = oValue.value
        elif isinstance(oValue, Name):
            temp = named_value_lookup.get(oValue.id.lower())
            if temp is not None:
                my_params[index] = int(temp)
            else:
                if int(id) in [17, 29, 30, 21007]:
                    upon = decode_upon(oValue.id)
                    my_params[index] = upon
                if int(id) in [43, 14001, 14012]:
                    buttonstr = oValue.id[-1].lower()
                    directionstr = oValue.id[:-1].lower()
                    my_params[index] = (int(named_button_lookup[buttonstr]) << 8) + int(
                        named_direction_lookup[directionstr])
        elif isinstance(oValue, UnaryOp):
            my_params[index] = -oValue.operand.value
        else:
            raise Exception("Unknown Type" + str(type(oValue)))
    binary_output.write(struct.pack(MODE + "I", int(id)))
    if "format" in cmd_data:
        for i, v1 in enumerate(my_params):
            if isinstance(v1, str):
                my_params[i] = v1.encode()
        binary_output.write(struct.pack(MODE + cmd_data["format"], *my_params))
    else:
        binary_output.write(my_params[0].encode())


class Rebuilder(astor.ExplicitNodeVisitor):
    def visit_Module(self, node):
        global binary_output
        global root
        root = node
        state_count = 0
        binary_output.write(struct.pack(MODE + "I", state_count))
        for function in node.body:
            if type(function) != FunctionDef:
                raise Exception("Root level elements must be functions")
            if function.decorator_list[0].id != "State":
                continue
            function._index = state_count
            state_count += 1
            if function.name.startswith('__') and function.name[2].isdigit():
                function.name = function.name[2:]
            if '__sp__' in function.name:
                function.name.replace('__sp__', ' ')
            if '__qu__' in function.name:
                function.name.replace('__qu__', '?')
            if '__at__' in function.name:
                function.name.replace('__at__', '@')
            if "__ds__" in function.name:
                function.name.replace('__ds__', '-' )
            bytelog = function.name.encode()
            binary_output.write(struct.pack(MODE + "32sI", function.name.encode(), 0xFADEF00D))
        node._dataStart = binary_output.tell()
        binary_output.seek(0)
        binary_output.write(struct.pack(MODE + "I", state_count))
        for childNode in node.body:
            self.visit_RootFunctionDef(childNode)

    def visit_Str(self, node):
        pass

    def visit_RootFunctionDef(self, node):
        global binary_output, root
        binary_output.seek(0, 2)
        if len(node.decorator_list) == 1:
            if node.decorator_list[0].id == "State":
                # Write offset into state table
                startOffset = binary_output.tell() - root._dataStart
                binary_output.seek(4 + 36 * node._index + 32)
                binary_output.write(struct.pack(MODE + "I", startOffset))
                binary_output.seek(0, 2)
                if node.name.startswith('__') and node.name[2].isdigit():
                    node.name = node.name[2:]
                if '__sp__' in node.name:
                    node.name.replace('__sp__', ' ')
                if '__qu__' in node.name:
                    node.name.replace('__qu__', '?')
                if '__at__' in node.name:
                    node.name.replace('__at__', '@')
                if "__ds__" in node.name:
                    node.name.replace('__ds__', '-' )
                write_command_by_name("startState", [node.name])
                self.visit_body(node.body)
                write_command_by_name("endState", [])
            else:
                if node.name.startswith('__') and node.name[2].isdigit():
                    node.name = node.name[2:]
                if '__sp__' in node.name:
                    node.name.replace('__sp__', ' ')
                if '__qu__' in node.name:
                    node.name.replace('__qu__', '?')
                if '__at__' in node.name:
                    node.name.replace('__at__', '@')
                if "__ds__" in node.name:
                    node.name.replace('__ds__', '-' )
                write_command_by_name("startSubroutine", [node.name])
                self.visit_body(node.body)
                write_command_by_name("endSubroutine", [])
        else:
            raise Exception("haven't implemented this")

    def visit_Pass(self, node):
        pass

    def visit_Call(self, node):
        node.func.id = node.func.id.lower()
        # We have a function call. Is it a named function or is it UnknownXXXXX
        if "unknown" in node.func.id:
            cmdId = node.func.id.replace("unknown", "")
        elif node.func.id in command_db_lookup:
            cmdId = command_db_lookup[node.func.id]["id"]
        else:
            raise Exception("Unknown Command " + node.func.id)
        write_command_by_id(cmdId, node.args)

    def visit_FunctionDef(self, node):
        node.name = node.name.lower()
        if "upon" not in node.name:
            raise Exception("inner functions are used for upon handlers only")
        write_command_by_name("upon", [decode_upon(node.name)])
        self.visit_body(node.body)
        write_command_by_name("endUpon", [])

    def visit_If(self, node):
        find = False
        try:
            node.body[0].value.func.id = node.body[0].value.func.id.lower()
            find = node.body[0].value.func.id == "conditionalsendtolabel"
        except:
            pass
        if isinstance(node.test, Name) and find:
            write_command_by_id("18", [node.body[0].value.args[0]] + decode_var(node.test))
        elif isinstance(node.test, Name):
            # This is if(SLOT) we need to find out slot index and write it as param of if
            write_command_by_name("if", decode_var(node.test))
            self.visit_body(node.body)
            write_command_by_name("endIf", [])
            if len(node.orelse) > 0:
                write_command_by_name("else", [])
                self.visit_body(node.orelse)
                write_command_by_name("endElse", [])
        elif isinstance(node.test, UnaryOp) and isinstance(node.test.operand, Name):
            # This is if(SLOT) we need to find out slot index and write it as param of if
            write_command_by_name("ifNot", decode_var(node.test.operand))
            self.visit_body(node.body)
            write_command_by_name("endIfNot", [])
            if len(node.orelse) > 0:
                write_command_by_name("else", [])
                self.visit_body(node.orelse)
                write_command_by_name("endElse", [])
        elif (isinstance(node.test, Call) or isinstance(node.test, Compare)) and find:
            self.visit(node.test)
            write_command_by_id("18", [node.body[0].value.args[0], 2, 0])
        elif isinstance(node.test, Call) or isinstance(node.test, Compare):
            self.visit(node.test)
            write_command_by_name("if", [2, 0])
            self.visit_body(node.body)
            write_command_by_name("endIf", [])
            if len(node.orelse) > 0:
                write_command_by_name("else", [])
                self.visit_body(node.orelse)
                write_command_by_name("endElse", [])
        elif isinstance(node.test, UnaryOp) and (
                isinstance(node.test.operand, Call) or isinstance(node.test.operand, Compare)):
            self.visit(node.test.operand)
            write_command_by_name("ifNot", [2, 0])
            self.visit_body(node.body)
            write_command_by_name("endIfNot", [])
            if len(node.orelse) > 0:
                write_command_by_name("else", [])
                self.visit_body(node.orelse)
                write_command_by_name("endElse", [])
        else:
            print("UNHANDLED IF"), astor.dump_tree(node)

        # If(SLOT)
        # If(Expr)
        # If(UnaryOp(Expr))

    def visit_Assign(self, node):
        if isinstance(node.value, BinOp):
            params = []
            if isinstance(node.value.op, Add):
                params.append(0)
            elif isinstance(node.value.op, Sub):
                params.append(1)
            elif isinstance(node.value.op, Mult):
                params.append(2)
            elif isinstance(node.value.op, Div):
                params.append(3)
            else:
                print("UNIMPLEMENTED BINOP", astor.dump_tree(node))
                raise Exception("Unknown Operation!")
            write_command_by_name("ModifyVar_", params + decode_var(node.targets[0]) + decode_var(node.value.right))
        else:
            write_command_by_name("StoreValue", decode_var(node.targets[0]) + decode_var(node.value))

    def visit_Compare(self, node):
        params = []
        if isinstance(node.ops[0], Eq):
            params.append(9)
        elif isinstance(node.ops[0], Gt):
            params.append(10)
        elif isinstance(node.ops[0], Lt):
            params.append(11)
        elif isinstance(node.ops[0], GtE):
            params.append(12)
        elif isinstance(node.ops[0], LtE):
            params.append(13)
        else:
            print("UNIMPLEMENTED BINOP", astor.dump_tree(node))
            raise Exception("Unknown Compare")
        write_command_by_name("op", params + decode_var(node.left) + decode_var(node.comparators[0]))

    def visit_body(self, nodebody):
        try:
            for childNode in nodebody:
                self.visit(childNode)
        except Exception as e:
            print(e, "\n" + astor.dump_tree(childNode))

    def visit_Expr(self, node):
        self.visit(node.value)

    def generic_visit(self, node):
        print(type(node).__name__)


def rebuild_bbscript(filename, output_path):
    global binary_output
    output = os.path.join(output_path, os.path.split(filename)[1].split('.')[0]  + ".bin")
    sourceAST = astor.code_to_ast.parse_file(filename)
    binary_output = open(output, "wb")
    Rebuilder().visit(sourceAST)
    binary_output.close()


if __name__ == '__main__':
    if len(sys.argv) not in [2, 3] or sys.argv[1].split(".")[-1] != "py":
        print("Usage:BBCF_Script_Rebuilder.py scr_xx.bin outdir")
        print("Default output directory if left blank is the input file's directory.")
        sys.exit(1)
    if len(sys.argv) == 2:
        rebuild_bbscript(sys.argv[1], os.path.split(sys.argv[1])[0])
    else:
        rebuild_bbscript(sys.argv[1], sys.argv[2])
    print("\033[96mcomplete\033[0m")
