package core

type Provider interface {
	Name() string
	IsAvailable() bool
	Install(packages []string) error
	Uninstall(packages []string) error
	Upgrade(packages []string) error
	ListPackages() []Package
	Search(query string) []Package
	Clean() error
}

type Registry struct {
	order     []string
	providers map[string]Provider
}

func NewRegistry(providers ...Provider) Registry {
	ordered := make([]string, 0, len(providers))
	index := make(map[string]Provider, len(providers))
	for _, provider := range providers {
		ordered = append(ordered, provider.Name())
		index[provider.Name()] = provider
	}
	return Registry{order: ordered, providers: index}
}

func (r Registry) Order() []string {
	return append([]string(nil), r.order...)
}

func (r Registry) All() map[string]Provider {
	all := make(map[string]Provider, len(r.providers))
	for name, provider := range r.providers {
		all[name] = provider
	}
	return all
}

func (r Registry) Get(name string) (Provider, bool) {
	provider, ok := r.providers[name]
	return provider, ok
}

func (r Registry) Available() map[string]Provider {
	available := make(map[string]Provider)
	for _, name := range r.order {
		provider := r.providers[name]
		if provider.IsAvailable() {
			available[name] = provider
		}
	}
	return available
}
