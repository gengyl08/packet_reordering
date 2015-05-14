package main

import (
	"flag"
	"log"
	"net"
	"sync"
	"time"
)

func handleConnection(conn net.Conn) {
	b := make([]byte, 32000)
	for {
		_, err := conn.Read(b)
		if err != nil {
			break
		}
	}
	conn.Close()
	log.Printf("Closed %v", conn.RemoteAddr())
}

func Server(addr string) {
	log.Printf("Listening on %s", addr)
	ln, err := net.Listen("tcp", addr)
	if err != nil {
		log.Fatalf("error %v on listen", err)
	}

	for {
		conn, err := ln.Accept()
		if err != nil {
			continue
		}

		log.Printf("Accepting connection from %v", conn.RemoteAddr())
		go handleConnection(conn)
	}
}

func oneConnection(addr string, duration_seconds int) {
	conn, err := net.Dial("tcp", addr)
	if err != nil {
		log.Printf("Error connecting to %s: %v", addr, err)
		return
	}

	log.Printf("Connected to %s", conn.RemoteAddr())
	finish := time.Now().Add(time.Duration(duration_seconds) * time.Second)
	data := make([]byte, 32000) // write buffer dummy data

	// send as fast as possible
	for time.Now().Before(finish) {
		conn.SetWriteDeadline(time.Now().Add(2 * time.Second))
		_, err := conn.Write(data)
		if err != nil {
			log.Printf("Error sending data to %s: %v", addr, err)
			return
		}
	}
	log.Printf("Done")
}

func Client(addr string, parallelism int, duration_seconds int) {
	var wgclient sync.WaitGroup
	for i := 0; i < parallelism; i++ {
		wgclient.Add(1)
		go func() {
			defer wgclient.Done()
			oneConnection(addr, duration_seconds)
		}()
	}
	wgclient.Wait()
}

func main() {
	server := flag.Bool("server", false, "run as server")
	client := flag.Bool("client", true, "run as client")
	addr := flag.String("addr", ":9876",
		"ip:port to connect to (when client) or "+
			"ip:port to listen on (when server)")
	parallelism := flag.Int("parallelism", 10,
		"Number of connections (when client)")
	duration_seconds := flag.Int("t", 100,
		"Duration of client connections (in seconds)")

	flag.Parse()

	// These are blocking calls.  So call with either server/client
	// set to true but not both.
	if *server == true {
		Server(*addr)
	}

	if *client == true {
		Client(*addr, *parallelism, *duration_seconds)
	}
}
