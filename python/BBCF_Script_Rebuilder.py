import module.astor as astor

import os, struct, json, sys, copy, itertools
from ast import *
import operator as pyOperator
from BBCF_Script_Parser import input_san, upon_0, upon_1, animation_san, condition_san
upon_san = upon_0 + upon_1

GAME = "BBCF"
slot_0_temp = Name("SLOT_0")

command_db_lookup = {}
slot_db_lookup = {}
named_value_lookup = {}
named_button_lookup = {}
named_direction_lookup = {}
upon_db_lookup = {}
animation_db_lookup = {}
move_condition_db_lookup = {}

MODE = "<"
error = False

sys.setrecursionlimit(20000000)

def load_json(path_from_static):
    try:
        return json.loads(open(os.path.join(os.path.dirname(sys.argv[0]), "static_db/" + GAME + "/" + path_from_static)).read())
    except (IOError, json.decoder.JSONDecodeError):
        return {}
    
def decode_op(node):
    if isinstance(node, UnaryOp) and isinstance(node.op, Invert):
        return 14
    elif isinstance(node, BinOp) or isinstance(node, BoolOp):
        if isinstance(node.op, Add):
            return 0
        elif isinstance(node.op, Sub):
            return 1
        elif isinstance(node.op, Mult):
            return 2
        elif isinstance(node.op, Div):
            return 3
        elif isinstance(node.op, Mod):
            return 4
        elif isinstance(node.op, And):
            return 5
        elif isinstance(node.op, Or):
            return 6
        elif isinstance(node.op, BitAnd):
            return 7
        elif isinstance(node.op, BitOr):
            return 8
    elif isinstance(node, Compare):
        if isinstance(node.ops[0], Eq):
            return 9
        elif isinstance(node.ops[0], Gt):
            return 10
        elif isinstance(node.ops[0], Lt):
            return 11
        elif isinstance(node.ops[0], GtE):
            return 12
        elif isinstance(node.ops[0], LtE):
            return 13
        elif isinstance(node.ops[0], NotEq):
            return 15
    raise Exception("Unknown op", node)

def decode_move(value):
    value.id = value.id.lower()
    tmp = named_value_lookup.get(value.id)
    if tmp is not None:
        return int(tmp)
    else:
        if value.id.replace("input_", "")[:2] == '0x':
            try:
                return int(value.id.replace("input_", ""), 16)
            except ValueError:
                pass
        buttonstr = value.id[-1]
        directionstr = value.id[:-1]
        return (int(named_button_lookup[buttonstr]) << 8) + int(
            named_direction_lookup[directionstr])

def decode_upon(value):
    value = value.lower().replace("upon_", "")
    if value in upon_db_lookup:
        return int(upon_db_lookup[value])
    else:
        return int(value)


def decode_var(node):
    if isinstance(node, UnaryOp):
        return [0, -node.operand.value]
    elif isinstance(node, Constant):
        return [0, node.value]
    elif node.id.lower().replace("slot_", "") in slot_db_lookup:
        return [2, int(slot_db_lookup[node.id.lower().replace("slot_", "")])]
    else:
        try:
            return [2, int(node.id.lower().replace("slot_", ""))]
        except ValueError:
            raise Exception("Unknown SLOT " + node.id, node)
        
        
def decode_condition(value):
    value.id = value.id.lower()
    tmp = move_condition_db_lookup.get(value.id)
    if tmp is not None:
        return int(tmp)
    else:
        return int(value.id)
    


def write_command_by_name(name, params):
    cmd_data = command_db_lookup[name.lower()]
    write_command_by_id(cmd_data["id"], params)


def write_command_by_id(command, params):
    global output_buffer
    cmd_data = command_db[command]
    if command in unknown_list:
        return
    command = int(command)
    if "type_check" in cmd_data:
        type_check = cmd_data["type_check"]
        type_check.sort()
        n = len(params) + len(type_check)
        for i in range(n):
            if i in type_check:
                var = decode_var(params[i])
                params.insert(i, var[0])
                params[i+1] = var[1]
    my_params = list(params)
    for index, value in enumerate(my_params):
        if isinstance(value, str):
            pass
        elif isinstance(value, int):
            pass
        elif isinstance(value, float):
            pass
        elif isinstance(value, Constant):
            my_params[index] = value.value
        elif isinstance(value, Name):
            if command in input_san:
                my_params[index] = decode_move(value)
            elif command in upon_san:
                my_params[index] = decode_upon(value.id)
            elif command in animation_san:
                s = value.id.lower()
                if s in animation_db_lookup:
                    my_params[index] = int(animation_db_lookup[s])
                else:
                    my_params[index] = int(s)
            elif command in condition_san:
                my_params[index] = decode_condition(value)
        elif isinstance(value, UnaryOp):
            my_params[index] = -value.operand.value
        else:
            raise Exception("Unknown type " + str(type(value)))
    if command in [11058, 22019] and len(my_params) == 1:
        new_params = []
        for attribute in "HBFPT":
            if attribute in my_params[0]:
                new_params.append(1)
            else:
                new_params.append(0)
        my_params = new_params
    output_buffer.write(struct.pack(MODE + "I", int(command)))
    for i, v1 in enumerate(my_params):
        if isinstance(v1, str):
            my_params[i] = v1.encode()
    if "format" in cmd_data:
        output_buffer.write(struct.pack(MODE + cmd_data["format"], *my_params))
    else:
        output_buffer.write(struct.pack(MODE + str(cmd_data["size"] - 4) + "s", *my_params))

def is_operation(value):
    return isinstance(value, Compare) or isinstance(value, BinOp) or isinstance(value, BoolOp) or (isinstance(value, UnaryOp) and isinstance(value.op, Invert))

class MacroExpander(NodeTransformer):
    def __init__(self, argdict):
        self.argdict = argdict
        self.OpToFunc = {

                # boolOps dont have functions and are handled separately

                # binOp:
                Add: pyOperator.add,
                Sub: pyOperator.sub,
                Mult: pyOperator.mul,
                # MatMult: pyOperator.matmul,
                Div: pyOperator.floordiv, # docs state this should be truediv, which allows floating points, but this matches the games functionality closer
                Mod: pyOperator.mod,
                Pow: pyOperator.pow,
                LShift: pyOperator.lshift,
                RShift: pyOperator.rshift,
                BitOr: pyOperator.or_,
                BitXor: pyOperator.xor,
                BitAnd: pyOperator.and_,
                # FloorDiv: pyOperator.floordiv

                # unaryOp:

                Invert: pyOperator.invert,
                Not: pyOperator.not_,
                USub: pyOperator.neg,
                UAdd: pyOperator.pos,


                # cmpOp

                Eq: pyOperator.eq,
                NotEq: pyOperator.ne,
                Lt: pyOperator.lt,
                LtE: pyOperator.le,
                Gt: pyOperator.gt,
                GtE: pyOperator.ge,
                # Is: pyOperator.is_,
                # IsNot: pyOperator.is_not,
                # In: pyOperator.in_,
                # NotIn: pyOperator.notin,

            }

    def visit_Name(self, node):
        if node.id in self.argdict:
            return self.argdict[node.id]
        return node

    def visit_BoolOp(self, node):
        node = self.generic_visit(node)

        if not isinstance(node.values[0], Constant) or not isinstance(node.values[1], Constant):
            return node

        # apparently this isnt actually how python handles bool comparisons but 
        # i dont care because its shit
        if isinstance(node.op, And):
            return Constant(pyOperator.truth(node.values[0].value) and pyOperator.truth(node.values[1].value))
        else:
            return Constant(pyOperator.truth(node.values[0].value) or pyOperator.truth(node.values[1].value))

    # was worried this wouldn't follow order of operations but it just
    # kinda somehow does idk im not going to question it
    def visit_BinOp(self, node):
        node = self.generic_visit(node)

        if not isinstance(node.left, Constant) or not isinstance(node.right, Constant):
            return node

        node = Constant(self.OpToFunc[type(node.op)](node.left.value, node.right.value))

        return node

    def visit_UnaryOp(self, node):
        node = self.generic_visit(node)

        if not isinstance(node.operand, Constant):
            return node

        node = Constant(self.OpToFunc[type(node.op)](node.operand.value))
        return node
    
    def resolve_Is(self, a, b):
        return Constant(a.__class__.__name__ == b.id)
    def resolve_IsNot(self, a, b):
        return Constant(a.__class__.__name__ != b.id)

    def visit_Compare(self, node):
        node = self.generic_visit(node)

        left = node.left

        if len(node.ops) == 1 and isinstance(node.comparators[0], Name):
            if isinstance(node.ops[0], Is):
                return self.resolve_Is(left, node.comparators[0])
            elif isinstance(node.ops[0], IsNot):
                return self.resolve_IsNot(left, node.comparators[0])

        if not isinstance(left, Constant):
            return node

        result = 1

        for i, right in enumerate(node.comparators):

            # this can technically be simplified even with a constant 
            # but i dont wanna write that code
            if not isinstance(right, Constant):
                return node

            result = result and self.OpToFunc[type(node.ops[i])](left.value, right.value)
            if not result:
                break

            left = right

        return Constant(result)

    def visit_For(self, node):

        # do this check first or it will be replaced with a constant
        # and give unhelpful error messages
        VarName = node.target.id
        if VarName in self.argdict.keys():
            raise Exception("Variable name " + VarName + " already used in macro context", node)

        if (not (isinstance(node.iter, Name) and node.iter.id in self.argdict.keys())):
            raise Exception("Attempt to iterate over something other than a vararg list, this is unsupported", node)

        node.iter = self.argdict[node.iter.id]
        retnodes = []
        
        for i, val in enumerate(node.iter):
            body = copy.deepcopy(node.body)
            self.argdict[VarName] = val
            for k, val2 in enumerate(body):
                retval = self.visit(val2)
                if isinstance(retval, list):
                    retnodes += retval
                else:
                    retnodes.append(retval)

        del self.argdict[VarName]

        return retnodes

    def visit_While(self, node):

        if (not isinstance(node.test, Compare) or len(node.test.ops) != 1):
            raise Exception("Unsupported test on Macro while statement, while statements should always be formatted: 'while i < n' where i is a variable name to store the current number of iterations, and n is a compiletime constant number (or an expression that evaluates to such) representing the amount of iterations to generate", node)

        if (node.test.left.id in self.argdict.keys()):
            raise Exception("Variable " + node.test.left.id + " already used in macro context", node)

        node.test = self.generic_visit(node.test)

        if (not isinstance(node.test.ops[0], Lt)):
            raise Exception("Unsupported Operator In While Loop Condition", node)

        if (not isinstance(node.test.comparators[0], Constant)):
            raise Exception("Iterator is being compared against a value that is not a compiletime constant, we dont know how many iterations to generate", node)

        retnodes = []

        for i in range(0, node.test.comparators[0].value):
            body = copy.deepcopy(node.body)
            self.argdict[node.test.left.id] = Constant(i)

            for k, val in enumerate(body):
                retval = self.visit(val)
                if isinstance(retval, list):
                    retnodes += retval
                else:
                    retnodes.append(retval)

        del self.argdict[node.test.left.id]
        return retnodes


    def visit_If(self, node):
        node = self.generic_visit(node)
        if isinstance(node.test, Constant) and not pyOperator.truth(node.test.value):
            return node.orelse
        elif isinstance(node.test, Constant) and pyOperator.truth(node.test.value):
            return node.body

        return node

    def visit_Call(self, node):
        node = self.generic_visit(node)

        if (node.func.id == "str" and len(node.args) == 1):
            if isinstance(node.args[0], Constant):
                return Constant(str(node.args[0].value))
            elif isinstance(node.args[0], Name):
                return Constant(node.args[0].id)
            else:
                return Constant(astor.to_source(node.args[0])[:-1]) # to_source always adds a newline to the end of its strings
        
        return node

class Rebuilder(astor.ExplicitNodeVisitor):
    MacroDict = {}

    def visit_Module(self, node):
        global output_buffer, root
        root = node
        state_count = 0
        output_buffer.write(struct.pack(MODE + "I", state_count))
        for function in node.body:
            if type(function) != FunctionDef:
                raise Exception("Root level elements must be functions", function)
            if len(function.decorator_list) == 0 or function.decorator_list[0].id.lower() != "state":
                continue
            function._index = state_count
            state_count += 1
            if function.name.startswith('__') and function.name[2].isdigit():
                function.name = function.name[2:]
            function.name.replace('__sp__', ' ').replace('__qu__', '?').replace('__at__', '@').replace('__ds__', '-' )
            bytelog = function.name.encode()
            output_buffer.write(struct.pack(MODE + "32sI", function.name.encode(), 0xFADEF00D))
        node._dataStart = output_buffer.tell()
        output_buffer.seek(0)
        output_buffer.write(struct.pack(MODE + "I", state_count))
        for child_node in node.body:
            self.visit_RootFunctionDef(child_node)
    
    def visit_Str(self, node):
        pass

    def visit_RootFunctionDef(self, node):
        global output_buffer, root
        output_buffer.seek(0, 2)
        if len(node.decorator_list) == 1:
            if node.decorator_list[0].id.lower() == "state":
                # Write offset into state table
                start_offset = output_buffer.tell() - root._dataStart
                output_buffer.seek(4 + 36 * node._index + 32)
                output_buffer.write(struct.pack(MODE + "I", start_offset))
                output_buffer.seek(0, 2)
                if node.name.startswith('__') and node.name[2].isdigit():
                    node.name = node.name[2:]
                node.name.replace('__sp__', ' ').replace('__qu__', '?').replace('__at__', '@').replace('__ds__', '-' )
                write_command_by_id("0", [node.name])
                self.visit_body(node.body)
                write_command_by_id("1", [])
            elif node.decorator_list[0].id.lower() == "subroutine":
                if node.name.startswith('__') and node.name[2].isdigit():
                    node.name = node.name[2:]
                node.name.replace('__sp__', ' ').replace('__qu__', '?').replace('__at__', '@').replace('__ds__', '-' )
                write_command_by_id("8", [node.name])
                self.visit_body(node.body)
                write_command_by_id("9", [])
            elif node.decorator_list[0].id.lower() == "macro":
                if (node.name.lower() in self.MacroDict.keys()):
                    raise Exception("Redefinition of macro " + node.name, node)
                if (node.name.lower() in command_db_lookup):
                    raise Exception("Name of macro " + node.name + " conflicts with name of regular command with id " + command_db_lookup[node.name.lower()]["id"], node)
                self.MacroDict[node.name.lower()] = node
            else:
                raise Exception("Unrecognized/Unsupported decorator: " + node.decorator_list[0].id.lower(), node)
                
        else:
            raise Exception("Root functions must have a decorator", node)

    def visit_Pass(self, node):
        pass

    def visit_Call(self, node):
        for index, value in enumerate(node.args):
            if isinstance(value, Call) or is_operation(value):
                self.visit_Assign(Assign([slot_0_temp], value))
                node.args[index] = slot_0_temp

        node.func.id = node.func.id.lower()
        # We have a function call. Is it a named function or is it UnknownXXXXX
        if "unknown" in node.func.id:
            cmd_id = node.func.id.replace("unknown", "")
        elif node.func.id in command_db_lookup:
            cmd_id = command_db_lookup[node.func.id]["id"]
        elif node.func.id in self.MacroDict.keys():
            self.visit_MacroCall(node)
            return
        else:
            raise Exception("Unknown command or macro", node)
        write_command_by_id(cmd_id, node.args)

    # Concerns def upon_ and applyFunctionToObject
    def visit_FunctionDef(self, node):
        if len(node.decorator_list) > 0 and "stateregister" in node.decorator_list[0].id.lower():
            if node.name.startswith('__') and node.name[2].isdigit():
                node.name = node.name[2:]
            node.name.replace('__sp__', ' ').replace('__qu__', '?').replace('__at__', '@').replace('__ds__', '-' )
            write_command_by_id("14001", [node.name, Name(node.args.args[0].arg)])
            self.visit_body(node.body)
            write_command_by_id("14002", [])
            return
        node.name = node.name.lower()
        if "upon" in node.name:
            write_command_by_id("15", [decode_upon(node.name)])
            self.visit_body(node.body)
            write_command_by_id("16", [])
        elif command_db["36"]["name"] in node.name:
            write_command_by_id("36", [int(node.name.replace(command_db["36"]["name"] + "_", ""))])
            self.visit_body(node.body)
            write_command_by_id("35", [])
        else:
            raise Exception("Prohibited inner function", node)


    def visit_If(self, node):
        def is_not(node_test):
            return isinstance(node_test, UnaryOp) and isinstance(node_test.op, Not)
        def is_slot(node_test):
            return isinstance(node_test, Name) or isinstance(node_test, Call) or is_operation(node_test)

        if is_slot(node.test):
            if isinstance(node.test, Name):
                write_command_by_id("4", [node.test])
            else:
                self.visit(node.test)
                write_command_by_id("4", [slot_0_temp])
            self.visit_body(node.body)
            write_command_by_id("5", [])
        elif is_not(node.test) and is_slot(node.test.operand):
            if isinstance(node.test.operand, Name):
                write_command_by_id("54", [node.test.operand])
            else:
                self.visit(node.test.operand)
                write_command_by_id("54", [slot_0_temp])
            self.visit_body(node.body)
            write_command_by_id("55", [])
        else:
            raise Exception("Unhandled if")
        if len(node.orelse) > 0:
            write_command_by_id("56", [])
            self.visit_body(node.orelse)
            write_command_by_id("57", [])

    def visit_UnaryOp(self, node):
        return

    def visit_BoolOp(self, node):
        for i, v in enumerate(node.values):
            if isinstance(v, Call) or is_operation(v):
                self.visit_Assign(Assign([slot_0_temp], v))
                node.values[i] = slot_0_temp
        self.visit_Assign(Assign([slot_0_temp], node))

    def visit_BinOp(self, node):
        v = node.left
        if isinstance(v, Call) or is_operation(v):
            self.visit_Assign(Assign([slot_0_temp], v))
            node.left = slot_0_temp
        v = node.right
        if isinstance(v, Call) or is_operation(v):
            self.visit_Assign(Assign([slot_0_temp], v))
            node.right = slot_0_temp
        self.visit_Assign(Assign([slot_0_temp], node))

    def visit_Compare(self, node):
        v = node.left
        if isinstance(v, Call) or is_operation(v):
            self.visit_Assign(Assign([slot_0_temp], v))
            node.left = slot_0_temp
        v = node.comparators[0]
        if isinstance(v, Call) or is_operation(v):
            self.visit_Assign(Assign([slot_0_temp], v))
            node.comparators[0] = slot_0_temp
        self.visit_Assign(Assign([slot_0_temp], node))

    def visit_Assign(self, node):
        aval = node.targets[0]
        if isinstance(node.value, Call):
            self.visit(node.value)
            if aval.id.lower() != "slot_0":
                node.value = slot_0_temp
                self.visit(node)
        elif isinstance(node.value, Name) or isinstance(node.value, Constant) or (isinstance(node.value, UnaryOp) and (isinstance(node.value.operand, Name) or isinstance(node.value.operand, Constant))) :
            # StoreValue
            write_command_by_id("41", [node.targets[0], node.value])
        else:
            op_id = [decode_op(node.value)]
            if isinstance(node.value, BinOp):
                lval = node.value.left
                rval = node.value.right
            elif isinstance(node.value, BoolOp):
                lval = node.value.values[0]
                rval = node.value.values[1]
            elif isinstance(node.value, Compare):
                lval = node.value.left
                rval = node.value.comparators[0]
            elif isinstance(node.value, UnaryOp) and isinstance(node.value.op, Invert):
                lval = node.value.operand.left
                rval = node.value.operand.right
            else:
                raise Exception("How did this happen")
            if isinstance(lval, Call) or is_operation(lval):
                self.visit(Assign([slot_0_temp], lval))
                lval = slot_0_temp
            if isinstance(rval, Call) or is_operation(rval):
                self.visit(Assign([slot_0_temp], rval))
                rval = slot_0_temp
            if aval.id.lower() == "slot_0":
                # op
                write_command_by_id("40", op_id + [lval, rval])
            elif isinstance(aval, Name) and isinstance(lval, Name) and aval.id.lower() == lval.id.lower():
                # ModifyVar
                write_command_by_id("49", op_id + [aval, rval])
            else:
                # Unknown47 / PrivateFunction
                write_command_by_id("47", op_id + [lval, rval, aval])

    def visit_body(self, nodebody):
        global output_buffer, error
        for childNode in nodebody:
            self.visit(childNode)

    def visit_Expr(self, node):
        self.visit(node.value)

    def visit_MacroCall(self, node):
        Macro = copy.deepcopy(self.MacroDict[node.func.id])

        if len(node.args) < len(Macro.args.args) or (len(node.args) > len(Macro.args.args) and Macro.args.vararg is None):
            raise Exception("Macro " + Macro.name + 
                            " called with incorrect number of arguments (expected " + 
                            str(len(Macro.args.args)) + ", got " + str(len(node.args)) + ")", node)

        ArgDict = {}

        if Macro.args.vararg is not None:
            ArgDict[Macro.args.vararg.arg] = []

        for i, val in enumerate(Macro.args.args):
            ArgDict[val.arg] = node.args[i]

        if Macro.args.vararg is not None:
            ArgDict[Macro.args.vararg.arg] = node.args[len(Macro.args.args):]


        ME = MacroExpander(ArgDict)

        newbody = []

        for i, v, in enumerate(Macro.body):
            result = ME.visit(v)

            if (isinstance(result, list)):
                newbody += result
            else:
                newbody.append(result)

        self.visit_body(newbody)


    def generic_visit(self, node):
        print(type(node).__name__)


def rebuild_bbscript(filename, output_path):
    global output_buffer
    output_name = os.path.join(output_path, os.path.split(filename)[1].split('.')[0] + "_error.bin")
    source_ast = astor.code_to_ast.parse_file(filename)
    output_buffer = open(output_name, "wb")
    try:
        Rebuilder().visit(source_ast)
    except Exception as e:
        if len(e.args) > 1:
            print("\033[91m", e.args[0], "\n", astor.to_source(e.args[1]), "at line ", e.args[1].lineno, "\033[0m", sep="")
        else:
            print("\033[91m", e, "\033[0m", sep="")

        if debug:
            output_buffer.close()
            os.replace(output_name, output_name.replace("_error.", "."))
        sys.exit(0)
    output_buffer.close()
    os.replace(output_name, output_name.replace("_error.", "."))


if __name__ == '__main__':
    flag_list = "Flags: --debug, --remove"
    debug = remove_unknown = False
    unknown_list = []
    input_file = None
    output_path = None

    for i, v in enumerate(sys.argv[1:]):
        if "-h" in v:
            print("Usage:" + GAME + "_Script_Rebuilder.py scr_xx.py outdir")
            print("Default output directory if left blank is the input file's directory.")
            print(flag_list)
            print("--debug: Create a scr_xx_error.bin file upon crashing")
            print("--remove: Delete the corresponding command name/id from the .bin file (THIS CAN BREAK FILES!!!)")
            sys.exit(0)
        if "--" in v:
            if "--debug" == v:
                debug = True
            elif "--remove" == v:
                remove_unknown = True
            else:
                raise Exception("Flag doesn't exist")
            continue
        if (sys.argv[i] == "--remove" or sys.argv[i][-1] == ",") and remove_unknown:
            unknown_list += v.split(",")
        elif input_file is None:
            input_file = v
        elif output_path is None:
            output_path = v

    if not input_file or input_file.split(".")[-1] != "py":
        print("Usage:" + GAME + "_Script_Rebuilder.py scr_xx.py outdir")
        print("Default output directory if left blank is the input file's directory.")
        print(flag_list)
        sys.exit(1)

    command_db = load_json("command_db.json")
    move_inputs = load_json("named_values/move_inputs.json")
    normal_inputs = load_json("named_values/normal_inputs.json")
    animation_db = load_json("named_values/hit_animation.json")
    move_condition_db = load_json("named_values/move_condition.json")
    upon_db = load_json("upon_db/global.json")
    slot_db = load_json("slot_db/global.json")
    object_db = load_json("object_db/global.json")

    #Checking for a custom slot/upon db
    character_name = os.path.split(input_file)[-1].replace("scr_", "").split(".")[0]
    if character_name[-2:] == "ea" and len(character_name) > 2:
        character_name = character_name[:-2]
    upon_db.update(load_json("upon_db/" + character_name + ".json"))
    slot_db.update(load_json("slot_db/" + character_name + ".json"))

    for k, v in command_db.items():
        v["id"] = k
        if "name" in v:
            v["name"] = v["name"].lower()
            command_db_lookup[v["name"]] = v
        else:
            command_db_lookup["unknown" + k] = v
    slot_db_lookup = {v.lower(): k for k, v in slot_db.items()}
    for k, v in move_inputs.items():
        if v is not True:
            named_value_lookup[v.lower()] = k
    for k, v in normal_inputs['grouped_values'].items():
        named_value_lookup[v.lower()] = k
    for k, v in normal_inputs['button_byte'].items():
        named_button_lookup[v.lower()] = k
    for k, v in normal_inputs['direction_byte'].items():
        named_direction_lookup[v.lower()] = k
    upon_db_lookup = {v.lower(): k for k, v in upon_db.items()}
    animation_db_lookup = {v.lower(): k for k, v in animation_db.items()}
    move_condition_db_lookup = {v.lower(): k for k, v in move_condition_db.items()}

    if remove_unknown:
        unknown_list = list(filter(None, unknown_list))
        for i, v in enumerate(unknown_list):
            if v in command_db:
                continue
            try:
                unknown_list[i] = command_db_lookup[v.lower()]['id']
            except KeyError:
                print("Unknown command '" + v + "'")
                sys.exit(1)

    if output_path is None:
        rebuild_bbscript(input_file, os.path.split(input_file)[0])
    else:
        rebuild_bbscript(input_file, output_path)
    print("\033[96m" + "complete" + "\033[0m")
