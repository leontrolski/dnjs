package main

func containsString(l []string, value string) bool {
	for _, v := range l {
		if v == value {
			return true
		}
	}
	return false
}
