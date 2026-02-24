package main

import (
	"encoding/json"
	"fmt"
)

type VM struct {
	PowerState string `json:"power_state"`
}

func main() {
	v := VM{PowerState: "poweredOn"}
	b, _ := json.Marshal(v)
	fmt.Println(string(b))
}
