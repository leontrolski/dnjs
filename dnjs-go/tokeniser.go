package main

import (
	"fmt"
	"io/ioutil"
	"strings"
)

type Token struct {
	Type  string
	Value string
	// if this starts with memory:// the source is stored in a global
	Filepath *string
	Pos      int
	Lineno   int
	Linepos  int
}

func (t Token) String() string {
	return fmt.Sprintf("<%s %s>", t.Type, t.Value)
}

// token types
var name = "name"
var str = "str"
var number = "number"
var template = "template"
var literal = "literal"

// # = => ( ) { } [ ] , : . ... ? === import from export default const `
var eof = "\x03" // end of text character
var unexpected = "unexpected"
var apply = "$"
var many = "*"
var dName = "dname"
var dMany = "d*"
var dBrack = "d["
var dBrace = "d{"
var atoms = []string{name, str, number, template, literal, dName}

var whitespace = " \t\f\r" // note no \n
var numberBegin = "-0123456789"
var numberAll = ".0123456789"
var nameBegin = "_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
var nameAll = "_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
var literalValues = []string{"null", "true", "false"}
var keywordValues = []string{"import", "from", "export", "default", "const"}
var punctuationValues = []string{"=", "=>", "(", ")", "{", "}", "[", "]", ",", ":", ".", "...", "?", "==="}
var interimPunctuationValues = []string{"..", "=="}

var globalCounter = 1
var globalSourceMap = map[string]string{}

func resetGlobalCounter() {
	globalCounter = 1
}

type TokenStream struct {
	Filepath      string
	Current       Token
	source        []rune
	pos           int
	lineno        int
	linepos       int
	templateDepth int
}

func TokenStreamFromFilepath(Filepath string) (TokenStream, error) {
	// could try do this more efficiently, but ah well
	dat, err := ioutil.ReadFile(Filepath)
	if err != nil {
		return TokenStream{}, err
	}
	tokenStream := TokenStream{
		Filepath:      Filepath,
		Current:       Token{},
		source:        []rune(strings.TrimRight(string(dat), whitespace+"\n")),
		pos:           0,
		lineno:        1,
		linepos:       0,
		templateDepth: 0,
	}
	tokenStream.Advance()
	return tokenStream, nil
}

func TokenStreamFromSource(Source string) TokenStream {
	Filepath := fmt.Sprintf("memory://%d", globalCounter)
	globalCounter += 1
	globalSourceMap[Filepath] = Source
	tokenStream := TokenStream{
		Filepath:      Filepath,
		Current:       Token{},
		source:        []rune(strings.TrimRight(Source, whitespace+"\n")),
		pos:           0,
		lineno:        1,
		linepos:       0,
		templateDepth: 0,
	}
	tokenStream.Advance()
	return tokenStream
}

func (ts *TokenStream) String() string {
	return fmt.Sprintf("<TokenStream file: %s>", ts.Filepath)
}

func (ts *TokenStream) Advance() {
	if ts.Current.Type == eof {
		return
	}
	current := ts.read()
	for {
		if current.Type != "\n" {
			break
		}
		current = ts.read()
	}
	ts.Current = current
}

func (ts *TokenStream) read() Token {
	char := func() string {
		if ts.pos == len(ts.source) {
			return eof
		}
		return string(ts.source[ts.pos])
	}
	inc := func() {
		ts.pos += 1
		ts.linepos += 1
	}
	incLine := func() {
		ts.linepos = 0
		ts.lineno += 1
	}
	gobble := func() string {
		before := char()
		inc()
		return before
	}
	atComment := func() bool {
		if ts.pos >= len(ts.source)-1 {
			return false
		}
		return string(ts.source[ts.pos])+string(ts.source[ts.pos+1]) == "//"
	}

	// eat up whitespace and comments
	for {
		if atComment() {
			inc()
			inc()
			for {
				if char() == "\n" || char() == eof {
					break
				}
				inc()
			}
		} else if strings.Contains(whitespace, char()) {
			inc()
		} else {
			break
		}
	}
	posBefore := ts.pos
	linenoBefore := ts.lineno
	lineposBefore := ts.linepos

	make := func(Type string, Value string) Token {
		return Token{
			Type:     Type,
			Value:    Value,
			Filepath: &ts.Filepath,
			Pos:      posBefore,
			Lineno:   linenoBefore,
			Linepos:  lineposBefore,
		}
	}

	t := char()
	inc()

	if t == eof {
		return make(eof, eof)
	}

	if t == "\n" {
		incLine()
		return make("\n", "\n")
	}

	if t == "\"" {
		for {
			thisChar := char()
			if thisChar == eof {
				return make(unexpected, t)
			}
			if thisChar == "\n" {
				t += gobble()
				return make(unexpected, t)
			}
			if thisChar == "\\" {
				gobble()
				t += gobble()
			} else if thisChar == "\"" {
				t += gobble()
				return make(str, t)
			} else {
				t += gobble()
			}
		}
	}

	if t == "`" || (t == "}" && ts.templateDepth > 0) {
		if t == "`" {
			ts.templateDepth += 1
		}
		for {
			thisChar := char()
			if thisChar == eof {
				return make(unexpected, t)
			}
			if thisChar == "\\" {
				gobble()
				t += gobble()
			} else if thisChar == "$" {
				t += gobble()
				if char() == "{" {
					t += gobble()
					if ([]rune(t))[0] == '`' {
						return make("`", t)
					}
					return make(template, t)
				}
			} else if thisChar == "`" {
				ts.templateDepth -= 1
				t += gobble()

				if ([]rune(t))[0] == '`' {
					return make("`", t)
				}
				return make(template, t)
			} else if thisChar == "\n" {
				incLine()
				t += gobble()
			} else {
				t += gobble()
			}
		}
	}

	if containsString(punctuationValues, t) {
		allPunctuationValues := append(punctuationValues, interimPunctuationValues...)
		if containsString(allPunctuationValues, t+char()) {
			t += gobble()
			if containsString(punctuationValues, t+char()) {
				t += gobble()
				return make(t, t)
			}
			if containsString(interimPunctuationValues, t) {
				return make(unexpected, t)
			}
			return make(t, t)
		}
		return make(t, t)
	}

	if strings.Contains(numberBegin, t) {
		seenDecimalPoint := false
		for {
			if !strings.Contains(numberAll, char()) {
				break
			}
			digit := char()
			inc()
			if digit == "." {
				if seenDecimalPoint {
					t += digit
					return make(unexpected, t)
				}
				seenDecimalPoint = true
			}
			t += digit
		}
		return make(number, t)
	}

	if strings.Contains(nameBegin, t) {
		for {
			if !strings.Contains(nameAll, char()) {
				break
			}
			t += gobble()
		}
		if containsString(keywordValues, t) {
			return make(t, t)
		}
		if containsString(literalValues, t) {
			return make(literal, t)
		}
		return make(name, t)
	}

	return make(unexpected, t)
}
