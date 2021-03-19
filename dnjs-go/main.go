package main

import (
  "fmt"
  "log"
  "os"
  "github.com/urfave/cli/v2"
)

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
    Name: "dnjs",
	Version: "v0.1.1",
    Flags: []cli.Flag {
		&cli.StringFlag{
		  Name: "lang",
		  Value: "english",
		  Usage: "language for the greeting",
		},
	  },
	Action: func(c *cli.Context) error {
		return fmt.Errorf("foooooo\nbar")
		name := "Nefertiti"
		if c.NArg() > 0 {
			name = c.Args().Get(0)
		}
		if c.String("lang") == "spanish" {
			fmt.Println("Hola", name)
		} else {
			fmt.Println("Hello", name)
		}
		return nil
	},
  }

  err := app.Run(os.Args)
  if err != nil {
    log.Fatal(err)
  }
}
