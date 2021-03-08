package main

import (
  "fmt"
  "log"
  "os"
  "github.com/urfave/cli/v2"
)

func main() {
  app := &cli.App{
    Name: "boom",
    Usage: "make an explosive entrance",
    Action: func(c *cli.Context) error {
      fmt.Println("boom! I say!")
      return nil
    },
  }

  err := app.Run(os.Args)
  if err != nil {
    log.Fatal(err)
  }
}
