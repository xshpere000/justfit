package main

import (
	"encoding/json"
	"fmt"
)

type VM struct {
	PowerState string `json:"powerState"`
}

func main() {
	v := VM{PowerState: "poweredOn"}
	b, _ := json.Marshal(v)
	fmt.Println(string(b))
}
