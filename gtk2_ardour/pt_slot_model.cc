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

#include <glibmm/ustring.h>

#include "ardour/amp.h"
#include "ardour/internal_send.h"
#include "ardour/plugin_insert.h"
#include "ardour/route.h"
#include "ardour/send.h"

#include "pt_slot_model.h"

using namespace ARDOUR;

std::string
PTSlotModel::short_label (std::string const& name, size_t max_chars)
{
	Glib::ustring u (name);
	if (u.size () <= max_chars) {
		return name;
	}
	return u.substr (0, max_chars > 1 ? max_chars - 1 : 1) + "…";
}

std::vector<PTInsertSlot>
PTSlotModel::collect_insert_slots (std::shared_ptr<Route> route)
{
	std::vector<PTInsertSlot> slots;
	if (!route) {
		return slots;
	}
	std::shared_ptr<Processor> amp = route->amp ();
	bool                       after_fader = false;

	route->foreach_processor ([&](std::weak_ptr<Processor> wp) {
		std::shared_ptr<Processor> p = wp.lock ();
		if (!p) {
			return;
		}
		if (p == amp) {
			after_fader = true;
			return;
		}
		if (after_fader || !p->display_to_user ()) {
			return;
		}
		std::shared_ptr<PluginInsert> pi = std::dynamic_pointer_cast<PluginInsert> (p);
		if (!pi) {
			return;
		}
		PTInsertSlot s;
		s.processor = p;
		s.label     = short_label (p->display_name ());
		s.active    = p->enabled ();
		slots.push_back (s);
	});
	return slots;
}

std::vector<PTSendSlot>
PTSlotModel::collect_send_slots (std::shared_ptr<Route> route)
{
	std::vector<PTSendSlot> slots;
	if (!route) {
		return slots;
	}
	std::shared_ptr<Processor> amp = route->amp ();
	bool                       after_fader = false;

	route->foreach_processor ([&](std::weak_ptr<Processor> wp) {
		std::shared_ptr<Processor> p = wp.lock ();
		if (!p) {
			return;
		}
		if (p == amp) {
			after_fader = true;
			return;
		}
		std::shared_ptr<Send> send = std::dynamic_pointer_cast<Send> (p);
		if (!send || send->is_foldback ()) {
			return;
		}
		PTSendSlot s;
		s.send      = send;
		s.active    = p->enabled ();
		s.pre_fader = !after_fader;
		std::shared_ptr<InternalSend> is = std::dynamic_pointer_cast<InternalSend> (send);
		if (is && is->target_route ()) {
			s.label = short_label (is->target_route ()->name ());
		} else {
			s.label = short_label (p->display_name ());
		}
		slots.push_back (s);
	});
	return slots;
}
