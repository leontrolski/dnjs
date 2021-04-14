package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"strings"

	"github.com/urfave/cli/v2"
)

func run(ctx *cli.Context) error {
	log.SetFlags(0)
	if ctx.NArg() == 0 {
		return fmt.Errorf("no arguments provided, try dnjs --help")
	}
	filepath := ctx.Args().Get(0)
	name := ctx.String("name")
	process := ctx.String("process")
	prettyFlag := ctx.Bool("pretty")
	htmlFlag := ctx.Bool("html")
	cssFlag := ctx.Bool("css")
	rawFlag := ctx.Bool("raw")
	csvFlag := ctx.Bool("csv")

	tokenStream := TokenStream{}
	err := fmt.Errorf("")
	if filepath == "-" {
		// could try do this more efficiently, but ah well
		source := ""
		scanner := bufio.NewScanner(os.Stdin)
		for scanner.Scan() {
			source += scanner.Text() + "\n"
		}
		if err := scanner.Err(); err != nil {
			return err
		}
		tokenStream = TokenStreamFromSource(source)
	} else {
		tokenStream, err = TokenStreamFromFilepath(filepath)
		if err != nil {
			return err
		}
	}
	module, err := interpret(&tokenStream)
	if err != nil {
		return err
	}

	var value Value
	var ok bool
	if name == "" {
		value = module.DefaultExport
		if value == missing {
			value = module.Value
		}
	} else {
		value, ok = module.Exports[name]
		if !ok {
			return fmt.Errorf("module %s does not export %s", filepath, name)
		}
	}

	switch v := value.(type) {
	case DnjsFunction:
		argValues := []Value{}
		numberOfArgs := len(v.ArgNames)
		if (ctx.NArg() - 1) != numberOfArgs {
			return fmt.Errorf("function needs calling with %d argument(s), see dnjs --help", numberOfArgs)
		}
		for i := 1; i <= numberOfArgs; i++ {
			argPath := ctx.Args().Get(i)
			tokenStream, err = TokenStreamFromFilepath(argPath)
			if err != nil {
				return err
			}
			module, err := interpret(&tokenStream)
			if err != nil {
				return err
			}
			argValue := module.DefaultExport
			if argValue == missing {
				argValue = module.Value
			}
			argValues = append(argValues, argValue)
		}
		value, err = v.Call(Node{}, argValues...)
		if err != nil {
			return err
		}
	default:
		if ctx.NArg() > 1 {
			return fmt.Errorf("too many arguments provided, try put them before the filename, or dnjs --help")
		}
	}

	if htmlFlag {
		htmlString, err := ToHtml(value)
		if err != nil {
			return err
		}
		fmt.Print(htmlString)
		return nil
	}

	if cssFlag {
		cssString, err := ToCss(value)
		if err != nil {
			return err
		}
		fmt.Print(cssString)
		return nil
	}

	if process != "" {
		processTokenStream := TokenStreamFromSource(process)
		processModule, err := interpret(&processTokenStream)
		if err != nil {
			return err
		}
		if processModule.Value == missing {
			return fmt.Errorf("--process argument must be a dnjs function")
		}
		processValue := processModule.Value
		switch processFunction := processValue.(type) {
		case DnjsFunction:
			value, err = processFunction.Call(Node{}, value)
			if err != nil {
				return err
			}
		default:
			return fmt.Errorf("--process argument must be a dnjs function")
		}
	}

	assertList := func(value Value) ([]Value, error) {
		switch typed := value.(type) {
		case []Value:
			return typed, nil
		default:
			return nil, fmt.Errorf("value cannot be converted to csv: " + fmt.Sprint(value))
		}
	}

	if csvFlag {
		typedValue, err := assertList(value)
		if err != nil {
			return err
		}
		for _, row := range typedValue {
			typedRow, err := assertList(row)
			if err != nil {
				return err
			}
			raws := []string{}
			for _, n := range typedRow {
				raw := []byte{}
				if rawFlag {
					raw, err = rawify(n)
				} else {
					raw, err = json.Marshal(n)
				}
				if err != nil {
					return err
				}
				raws = append(raws, string(raw))
			}
			fmt.Println(strings.Join(raws, ","))
		}
		return nil
	}

	if rawFlag {
		raw, err := rawify(value)
		if err != nil {
			return err
		}
		fmt.Println(string(raw))
		return nil
	}

	var jsonString []byte
	if prettyFlag {
		jsonString, err = json.MarshalIndent(value, "", "    ")
	} else {
		jsonString, err = json.Marshal(value)
	}
	if err != nil {
		return err
	}
	fmt.Println(string(jsonString[:]))
	return nil
}

func main() {
	cli.AppHelpTemplate = `Usage: dnjs [OPTIONS] FILENAME [ARGS]...

  FILENAME is the djns file to be evaluated. Remaining ARGS are files passed
  in as arguments to the evaluated dnjs if it is a function.

Options:
   {{range .VisibleFlags}}{{.}}
   {{end}}

Version:
   {{.Version}}
`
	app := &cli.App{
		Name:    "dnjs",
		Version: "v0.1.1",
		Flags: []cli.Flag{
			&cli.StringFlag{
				Name:  "name",
				Usage: "Pick an exported variable to return as opposed to the default.",
			},
			&cli.BoolFlag{
				Name:  "pretty",
				Usage: "Indent outputted JSON",
			},
			&cli.BoolFlag{
				Name:  "html",
				Usage: "Post process m(...) nodes to <html>",
			},
			&cli.BoolFlag{
				Name:  "css",
				Usage: "Post process to css",
			},
			&cli.StringFlag{
				Name:    "process",
				Aliases: []string{"p"},
				Value:   "",
				Usage:   "Post-process the output with another dnjs function, eg: 'd=>d.value'",
			},
			&cli.BoolFlag{
				Name:  "raw",
				Usage: "Print value as literal",
			},
			&cli.BoolFlag{
				Name:  "csv",
				Usage: "Print value as csv",
			},
		},
		Action: run,
	}

	err := app.Run(os.Args)
	if err != nil {
		log.Fatal(err)
	}
}

func rawify(value Value) ([]byte, error) {
	if value == nil {
		return []byte("null"), nil
	}
	switch v := value.(type) {
	case bool:
		jsonString, _ := json.Marshal(v)
		return jsonString, nil
	case string, int64, float64:
		return []byte(fmt.Sprint(v)), nil
	case []Value, map[Value]Value:
		jsonString, err := json.Marshal(v)
		if err != nil {
			return nil, err
		}
		return jsonString, nil
	default:
		return nil, fmt.Errorf("Unsupported type: " + fmt.Sprint(v))
	}
}
