# import this into lldb with a command like
# command script import bind.py
import lldb, shlex, re, sys
from string import ascii_lowercase
from os.path import expanduser


#Generate fresh variable names
varNum = 0
def freshVar():
    global varNum
    newVar = ascii_lowercase[varNum % 26] + str(varNum // 26)
    varNum += 1
    return newVar

#----------------------------------------bind command---------------------------------------------
# Usage: bind <expr> [name]
# Bind the expression to the supplied name if given, otherwise bind to a 
# freshly generated name.  The name that is bound, is of type: long ***,
# this way we can easily inspect memory using array indexing, Example:
#        (lldb) bind s->field1 field1
#        (lldb) print $field1[0][1][2]
def bind(debugger, command, result, dict):
    args = shlex.split(command)
    if len(args) == 1:
        name = freshVar()
        expr = command
    else:
        name = args[1]
        expr = args[0]
    print('Binding ' + expr + ' to ' + name)
    debugger.HandleCommand ('expression long *** $' + name + ' = (long***) ' + expr)

def untag_ghc(debugger, command, result, dict):
    args = shlex.split(command)
    if len(args) == 1:
        name = freshVar()
        expr = command
    else:
        name = args[1]
        expr = args[0]

    print('$' + name + ' is now bound to ' + expr)
    debugger.HandleCommand('expression long *** $' + name + ' = (long***) ' + '(((unsigned long)' + expr + ') & 0xFFFFFFFFFFFFFFF8)')


    
#----------------------------------------Break label command---------------------------------------------
def breakLab(debugger, command, result, dict):
    args = shlex.split(command)

    if len(args) < 1:
        print('Not enough arguments, usage: breakLab <label> [<condition>]')

    interpreter = lldb.debugger.GetCommandInterpreter()
    interpreter.HandleCommand('image lookup --symbol ' + args[0], result)
    res = re.search('0x[0-9a-z]*', str(result))
    if res is None:
        print('Could not find address of label \"' + args[0] + '\"')
        return
    else:
        address = res.group(0)
    if len(args) == 2:
        print('breakpoint set --address ' + address + ' --condition \'' + args[1] + '\'')
        interpreter.HandleCommand('breakpoint set --address ' + address + ' --condition \'' + args[1] + '\'', result)
    else:
        print('b ' + address)
        interpreter.HandleCommand('b ' + address, result)

#watchpoint command add -s p 1 
#The first argument is the heap object to watch and the second is an offset into that heap object
def mantWatch(debugger, command, result, dict):
    args = shlex.split(command)

    interpreter = lldb.debugger.GetCommandInterpreter()
    print("Setting watchpoint on " + args[0] + " + " + args[1] + "")


    interpreter.HandleCommand('command script add -f %s.updateWatchpoints updateWatchpoints' % __name__, result)
    print('command script add -f %s.updateWatchpoints updateWatchpoints' % __name__)
    print('---------')
    print(result)
    print('---------')

#examine a location in memory
def examine(debugger, command, result, dict):
    args = shlex.split(command)

    if len(args) != 2:
        print('incorrect number of arguments\nusage: examine <address> <number of bytes>')
        return

    interpreter = lldb.debugger.GetCommandInterpreter()
    interpreter.HandleCommand('x -s8 -fx -c' + args[1] + ' ' + args[0], result)

def restart(debugg, command, result, dict):
    interpreter = lldb.debugger.GetCommandInterpreter()
    print('rerunning \"' + command + '\"')
    interpreter.HandleCommand('kill', result)
    interpreter.HandleCommand('run ' + command, result)

def untilError(debugger, command, result, dict):
    interpreter = lldb.debugger.GetCommandInterpreter()
    interpreter.HandleCommand('breakpoint list', result)
    if re.search('name = \'exit\'', str(result)) is None:
        interpreter.HandleCommand('b exit', result)
    interpreter.HandleCommand('breakpoint list', result)
    breakpoints = re.findall("[0-9]+: name = \'.*\'", str(result))
    breakNum = None
    for b in breakpoints:
        if re.search("\'exit\'", b) is not None:
            breakNum = re.search("[0-9]+", b).group(0);
    if breakNum is None:
        print('Could not find exit breakpoint!')
        return

    print('breakpoint com add -o \"restart ' + command + '\" ' + breakNum)
    interpreter.HandleCommand('breakpoint com add -o \"restart ' + command + '\" ' + breakNum, result)

    interpreter.HandleCommand(command, result)

# Dump the output to a file.  You can specify a file explicitly, 
# dump to <home directory>/temp.txt by default 
# usage: toFile <command> [filename]
# typical usage: toFile run
def toFile(debugger, command, result, dict):
    args = shlex.split(command)
    if len(args) > 1:
        filename = args[1]
    else:
        home = expanduser("~")
        filename = home + "/temp.txt"
    f=open(filename,"w")
    debugger.SetOutputFileHandle(f,True);
    try:
        debugger.HandleCommand(command)  
        print('Done with command')
    except:
        print("inside exception handler!")
        f.close()
        debugger.SetOutputFileHandle(sys.stdout, True)
    f.close()
    debugger.SetOutputFileHandle(sys.stdout, True)

#----------------------------------------PrintBlock---------------------------------------------
# Usage: printBlock <label> <num>
# This command will lookup the label in the image, getting back an address, 
# and then disassemble <num> instructions after the address
def printBlock(debugger, command, result, dict):
    args = shlex.split(command)
    if len(args) != 2:
        print('usage: printBlock <label> <num>')
        return

    interpreter = lldb.debugger.GetCommandInterpreter()
    interpreter.HandleCommand('image lookup --symbol ' + args[0], result)
    res = re.search('0x[0-9a-z]*', str(result))
    if res is None:
        print('Could not find address of label \"' + args[0] + '\"')
        return
    else:
        address = res.group(0)

    interpreter.HandleCommand('disassemble --start-address ' + address + ' -c ' + args[1], result)
        

#
# code that runs when this script is imported into LLDB
#
def __lldb_init_module (debugger, dict):
    # This initializer is being run from LLDB in the embedded command interpreter
    # Add any commands contained in this module to LLDB
    debugger.HandleCommand('command script add -f %s.bind bind' % __name__)
    debugger.HandleCommand('command script add -f %s.breakLab breakLab' % __name__)
    debugger.HandleCommand('command script add -f %s.mantWatch mantWatch' % __name__)
    debugger.HandleCommand('command script add -f %s.examine examine' % __name__)
    debugger.HandleCommand('command script add -f %s.restart restart' % __name__)
    debugger.HandleCommand('command script add -f %s.untilError untilError' %__name__)
    debugger.HandleCommand('command script add -f %s.toFile toFile' %__name__)
    debugger.HandleCommand('command script add -f %s.untag_ghc untag_ghc' %__name__)
    debugger.HandleCommand('command script add -f %s.printBlock printBlock' %__name__)





















