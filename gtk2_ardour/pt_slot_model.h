/*
 * Copyright (C) 2026 Ahmed Hadjadj
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
 */

#pragma once

#include <memory>
#include <string>
#include <vector>

namespace ARDOUR {
	class Processor;
	class Route;
	class Send;
}

/* One Insert slot (A-E) of the Pro Tools style track header. */
struct PTInsertSlot {
	std::weak_ptr<ARDOUR::Processor> processor;
	std::string                      label;  /* short plugin name */
	bool                             active; /* false = bypassed */
};

/* One Send slot (A-E). */
struct PTSendSlot {
	std::weak_ptr<ARDOUR::Send> send;
	std::string                 label;     /* target bus name, or send name */
	bool                        active;
	bool                        pre_fader; /* placed before the fader */
};

namespace PTSlotModel {

	const size_t n_slots = 5;

	/* Truncate a processor name to max_chars, adding an ellipsis when cut. */
	std::string short_label (std::string const& name, size_t max_chars = 10);

	/* Pre-fader PluginInserts of the route in processor order. Not truncated:
	 * the caller shows the first n_slots and reports the rest in a tooltip. */
	std::vector<PTInsertSlot> collect_insert_slots (std::shared_ptr<ARDOUR::Route>);

	/* InternalSends (aux) and external Sends of the route in processor order. */
	std::vector<PTSendSlot> collect_send_slots (std::shared_ptr<ARDOUR::Route>);
}
